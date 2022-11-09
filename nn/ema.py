# modified from  https://github.com/rwightman/pytorch-image-models/blob/main/timm/utils/model_ema.py
# See also:
# - https://github.com/lucidrains/ema-pytorch/blob/main/ema_pytorch/ema_pytorch.py
# - https://github.com/fadel/pytorch_ema/blob/master/torch_ema/ema.py
# - https://github.com/benihime91/gale/blob/master/gale/collections/callbacks/ema.py#L20
# - https://www.zijianhu.com/post/pytorch/ema/
import copy
from typing import Optional

import torch
from torch import nn
from pydantic import validate_arguments


class ModelEMA(nn.Module):
    """Model Exponential Moving Average V2
    Keep a moving average of everything in the model state_dict (parameters and buffers).
    V2 of this module is simpler, it does not match params/buffers based on name but simply
    iterates in order. It works with torchscript (JIT of full model).
    This is intended to allow functionality like
    https://www.tensorflow.org/api_docs/python/tf/train/ExponentialMovingAverage
    A smoothed version of the weights is necessary for some training schemes to perform well.
    E.g. Google's hyper-params for training MNASNet, MobileNet-V3, EfficientNet, etc that use
    RMSprop with a short 2.4-3 epoch decay period and slow LR decay rate of .96-.99 requires EMA
    smoothing of weights to match results. Pay attention to the decay constant you are using
    relative to your update count per epoch.
    To keep EMA from using GPU resources, set device='cpu'. This will save a bit of memory but
    disable validation of the EMA weights. Validation will have to be done manually in a separate
    process, or after the training stops converging.
    This class is sensitive where it is initialized in the sequence of model init,
    GPU assignment and distributed training wrappers.
    """

    @validate_arguments
    def __init__(self, model, decay: float = 0.9999, device: Optional[str] = None):
        super().__init__()
        if decay <= 0.0 or decay >= 1.0:
            raise ValueError("Decay must be between 0 and 1")
        # make a copy of the model for accumulating moving average of weights
        self.module = copy.deepcopy(model)
        self.module.eval()
        self.decay = decay
        self.device = device  # perform ema on different device from model if set
        if self.device is not None:
            self.module.to(device=device)

    def _update(self, model, update_fn):
        with torch.no_grad():
            for ema_v, model_v in zip(
                self.module.state_dict().values(), model.state_dict().values()
            ):
                if self.device is not None:
                    model_v = model_v.to(device=self.device)
                ema_v.copy_(update_fn(ema_v, model_v))

    def update(self, model):
        self._update(
            model, update_fn=lambda e, m: self.decay * e + (1.0 - self.decay) * m
        )

    def set(self, model):
        self._update(model, update_fn=lambda e, m: m)


# Unlike ModelEMA which is intended for aside tracking, this is a full wrapper that uses EMA
# in eval mode
class EMAWrapper(nn.Module):
    @validate_arguments
    def __init__(self, model, decay: float = 0.9999):
        super().__init__()
        self.model = model
        self.ema = ModelEMA(self.model, decay=decay)

    @torch.no_grad()
    def update(self):
        if not self.training:
            raise RuntimeError(f"update should only be called in training mode")
        self.ema.update(self.model)

    def forward(self, *args, **kwargs):
        if self.training:
            self.model(*args, **kwargs)
        else:
            self.ema(*args, **kwargs)