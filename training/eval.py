"""Evaluate the saved Food-101 model on the official test split and write metrics.json.
Used to recover report metrics after a training run (e.g. interrupted before the
in-script evaluation). Run:  python eval.py
"""
import json, os
import tensorflow as tf
from train import build_dataset, read_split

DATA = "../food-101/food-101"
img_dir = os.path.join(DATA, "images")
meta = os.path.join(DATA, "meta")

classes = [c.strip() for c in open(os.path.join(meta, "classes.txt")) if c.strip()]
c2i = {c: i for i, c in enumerate(classes)}
test = read_split(meta, "test")
val_ds = build_dataset(img_dir, test, c2i, training=False)

model = tf.keras.models.load_model("artifacts/food101_mobilenetv2.keras")
top5 = tf.keras.metrics.SparseTopKCategoricalAccuracy(k=5, name="top5")
model.compile(loss="sparse_categorical_crossentropy", metrics=["accuracy", top5])

res = model.evaluate(val_ds, return_dict=True, verbose=1)
metrics = {
    "test_accuracy_top1": round(float(res["accuracy"]), 4),
    "test_accuracy_top5": round(float(res["top5"]), 4),
    "test_loss": round(float(res["loss"]), 4),
    "num_classes": len(classes),
    "train_images": len(read_split(meta, "train")),
    "test_images": len(test),
    "total_params": int(model.count_params()),
    "backbone": "MobileNetV2 (ImageNet) + transfer learning",
    "note": "best checkpoint; fine-tuning partially completed (CPU-limited run).",
}
json.dump(metrics, open("artifacts/metrics.json", "w"), indent=2)
print(json.dumps(metrics, indent=2))
