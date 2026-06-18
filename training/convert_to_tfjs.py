"""
Convert the trained Keras model to TensorFlow.js format so it can run
in-browser inside the Node-RED dashboard.

One-time install (Windows-safe — avoids uvloop, which can't build on Windows):
    pip install tensorflowjs==4.17.0 --no-deps
    pip install tensorflow-hub packaging six importlib_resources

Usage:
    python convert_to_tfjs.py

Outputs into ../node-red/model/:
    model.json          (graph + weight manifest)
    group1-shard*.bin   (weights)
    labels.json         (class names, copied alongside the model)

After this runs, copy the whole ../node-red/model/ folder to the other
laptop and point Node-RED's static path at it (see docs/DEPLOY.md).
"""

import os
import sys
import types
import shutil

# Windows fix: importing tensorflowjs 4.x eagerly loads converter paths we
# never use (decision-forest and JAX). Neither `tensorflow_decision_forests`
# nor `jax`/`jaxlib` have reliable Windows wheels. Since we only call
# save_keras_model, we stub those unused modules before importing tensorflowjs.
def _stub(name):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]

_stub("tensorflow_decision_forests")
_stub("tensorflow_hub")               # only used by the saved-model path
_jax = _stub("jax")
_jax_exp = _stub("jax.experimental")
_jax2tf = _stub("jax.experimental.jax2tf")
_jax.experimental = _jax_exp          # so `from jax.experimental import jax2tf`
_jax_exp.jax2tf = _jax2tf             # resolves against our stubs

import tensorflowjs as tfjs
import tensorflow as tf

SRC = "artifacts/food101_mobilenetv2.keras"
OUT = "../node-red/model"


def main():
    os.makedirs(OUT, exist_ok=True)
    model = tf.keras.models.load_model(SRC)
    tfjs.converters.save_keras_model(model, OUT)
    shutil.copy("artifacts/labels.json", os.path.join(OUT, "labels.json"))
    print(f"TensorFlow.js model written to {OUT}")
    print("Files:", os.listdir(OUT))


if __name__ == "__main__":
    main()
