"""
Food-101 classifier — transfer learning with MobileNetV2.

Trains on the Food-101 dataset and exports a Keras model that is later
converted to TensorFlow.js (see convert_to_tfjs.py) so it can run
in-browser inside the Node-RED dashboard.

Usage:
    python train.py --data ../food-101/food-101 --epochs 15

Outputs:
    artifacts/food101_mobilenetv2.keras   (full Keras model)
    artifacts/labels.json                  (class index -> name, ordered)

Notes:
- Uses the official Food-101 train/test split from meta/train.txt & test.txt.
- MobileNetV2 is chosen because it is small and fast in TensorFlow.js.
- Two phases: (1) train the head with the base frozen, (2) fine-tune the
  top of the base at a low learning rate.
"""

import argparse
import json
import os

import tensorflow as tf

IMG_SIZE = 224          # MobileNetV2 native input
BATCH = 32
AUTOTUNE = tf.data.AUTOTUNE


def read_split(meta_dir, split):
    """Read meta/{train,test}.txt -> list of 'class/imageid' relative paths."""
    with open(os.path.join(meta_dir, f"{split}.txt"), "r") as f:
        return [line.strip() for line in f if line.strip()]


def build_dataset(image_dir, items, class_to_idx, training):
    paths = [os.path.join(image_dir, item + ".jpg") for item in items]
    labels = [class_to_idx[item.split("/")[0]] for item in items]

    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        ds = ds.shuffle(8000, reshuffle_each_iteration=True)

    def load(path, label):
        img = tf.io.read_file(path)
        img = tf.io.decode_jpeg(img, channels=3)
        img = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
        # Augmentation lives in the DATA pipeline (not the model) so the saved
        # model stays clean and loadable by TensorFlow.js.
        if training:
            img = tf.image.random_flip_left_right(img)
            img = tf.image.random_brightness(img, 0.1)
            img = tf.clip_by_value(img, 0.0, 255.0)
        # MobileNetV2 preprocessing == scale to [-1, 1]. The browser does the
        # exact same thing (img/127.5 - 1), so inputs match at inference time.
        img = (img / 127.5) - 1.0
        return img, label

    ds = ds.map(load, num_parallel_calls=AUTOTUNE)
    return ds.batch(BATCH).prefetch(AUTOTUNE)


def build_model(num_classes):
    base = tf.keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base.trainable = False

    # Clean inference graph: base + head only. No augmentation / preprocessing
    # layers -> exports cleanly to TensorFlow.js (layers format).
    inputs = tf.keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    x = base(inputs, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    return tf.keras.Model(inputs, outputs), base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="path to food-101/food-101")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--fine_tune_epochs", type=int, default=5)
    ap.add_argument("--out", default="artifacts")
    # Smoke test: cap batches per epoch so the full pipeline can be validated
    # in minutes instead of hours. e.g. --steps_per_epoch 20 --val_steps 5
    ap.add_argument("--steps_per_epoch", type=int, default=None)
    ap.add_argument("--val_steps", type=int, default=None)
    args = ap.parse_args()

    image_dir = os.path.join(args.data, "images")
    meta_dir = os.path.join(args.data, "meta")
    os.makedirs(args.out, exist_ok=True)

    classes = [c.strip() for c in open(os.path.join(meta_dir, "classes.txt")) if c.strip()]
    class_to_idx = {c: i for i, c in enumerate(classes)}
    json.dump(classes, open(os.path.join(args.out, "labels.json"), "w"), indent=2)
    print(f"{len(classes)} classes")

    train_items = read_split(meta_dir, "train")
    test_items = read_split(meta_dir, "test")
    train_ds = build_dataset(image_dir, train_items, class_to_idx, training=True)
    val_ds = build_dataset(image_dir, test_items, class_to_idx, training=False)

    top5 = tf.keras.metrics.SparseTopKCategoricalAccuracy(k=5, name="top5")
    model, base = build_model(len(classes))
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy", top5],
    )

    ckpt = os.path.join(args.out, "food101_mobilenetv2.keras")
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(ckpt, save_best_only=True, monitor="val_accuracy"),
        tf.keras.callbacks.EarlyStopping(patience=4, restore_best_weights=True, monitor="val_accuracy"),
    ]

    fit_kw = {}
    if args.steps_per_epoch:
        fit_kw["steps_per_epoch"] = args.steps_per_epoch
    if args.val_steps:
        fit_kw["validation_steps"] = args.val_steps

    print("== Phase 1: train head (base frozen) ==")
    h1 = model.fit(train_ds, validation_data=val_ds, epochs=args.epochs, callbacks=callbacks, **fit_kw)

    print("== Phase 2: fine-tune top of base ==")
    base.trainable = True
    for layer in base.layers[:-30]:   # only unfreeze the last ~30 layers
        layer.trainable = False
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-5),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy", top5],
    )
    h2 = model.fit(train_ds, validation_data=val_ds, epochs=args.fine_tune_epochs, callbacks=callbacks, **fit_kw)

    model.save(ckpt)
    print(f"Saved -> {ckpt}")

    # --- save metrics + history for the report ---
    print("== Final evaluation on the test split ==")
    res = model.evaluate(val_ds, return_dict=True, **({"steps": args.val_steps} if args.val_steps else {}))
    metrics = {
        "test_accuracy_top1": round(float(res.get("accuracy", 0)), 4),
        "test_accuracy_top5": round(float(res.get("top5", 0)), 4),
        "test_loss": round(float(res.get("loss", 0)), 4),
        "num_classes": len(classes),
        "train_images": len(train_items),
        "test_images": len(test_items),
        "total_params": int(model.count_params()),
        "epochs_phase1": args.epochs,
        "epochs_phase2": args.fine_tune_epochs,
        "backbone": "MobileNetV2 (ImageNet)",
    }
    json.dump(metrics, open(os.path.join(args.out, "metrics.json"), "w"), indent=2)
    hist = {k: [float(x) for x in v] for k, v in {**h1.history, **{"ft_" + k: v for k, v in h2.history.items()}}.items()}
    json.dump(hist, open(os.path.join(args.out, "history.json"), "w"), indent=2)
    print("Metrics:", json.dumps(metrics, indent=2))
    print("Next: python convert_to_tfjs.py")


if __name__ == "__main__":
    main()
