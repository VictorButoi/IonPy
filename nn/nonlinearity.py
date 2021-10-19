import torch
from torch import nn


class Sine(nn.Module):
    def __init__(self, w0=1.0):
        super().__init__()
        self.w0 = w0

    def forward(self, x):
        return torch.sin(self.w0 * x)


_custom_nonlinearities = {"Sine": Sine}


def register_nonlinearity(nonlinearity):
    name = nonlinearity.__class__.__name__
    if hasattr(nn, name):
        raise ValueError(f"{name} already defined in torch.nn")
    if name in _custom_nonlinearities:
        raise ValueError(f"{name} already defined in pylot.nn.nonlinearity")
    _custom_nonlinearities[name] = nonlinearity


def get_nonlinearity(nonlinearity):
    if hasattr(nn, nonlinearity):
        return getattr(nn, nonlinearity)

    if nonlinearity in _custom_nonlinearities:
        return _custom_nonlinearities[nonlinearity]

    raise ValueError(f"nonlinearity {nonlinearity} not found")