import numpy as np

from prml.autodiff.core.array import Array, asarray
from prml.autodiff.core.config import config


class Function(object):
    enable_auto_broadcast = False

    def forward(self, *args, **kwargs):
        self.args = [self._convert2array(arg) for arg in args]
        if self.enable_auto_broadcast:
            self.args = self._autobroadcast(self.args)
        self.kwargs = kwargs
        out = self._forward(*tuple(arg.value for arg in self.args), **kwargs)
        out = Array(out)
        if config.enable_backprop:
            out.add_parent(self)
        return out

    def backward(self, delta, backprop_taskmanager):
        dargs = self._backward(
            delta,
            *tuple(arg.value for arg in self.args),
            **self.kwargs
        )
        if isinstance(dargs, tuple):
            for arg, darg in zip(self.args, dargs):
                arg._accumulate_gradient_from_child(darg)
                backprop_taskmanager.add_task(arg)
        else:
            self.args[0]._accumulate_gradient_from_child(dargs)
            backprop_taskmanager.add_task(self.args[0])

    def _out_depth(self):
        return max([arg._depth for arg in self.args]) + 1

    @staticmethod
    def _autobroadcast(arg):
        return broadcast(arg)

    def _forward(self, *args, **kwargs):
        raise NotImplementedError

    def _backward(self, *args, **kwargs):
        raise NotImplementedError

    @staticmethod
    def _convert2array(arg):
        if not isinstance(arg, Array):
            return asarray(arg)
        else:
            return arg


class BroadcastTo(Function):
    """
    Broadcast a tensor to an new shape
    """

    def __init__(self, shape):
        self.shape = shape

    def _forward(self, x):
        output = np.broadcast_to(x, self.shape)
        return output

    @staticmethod
    def _backward(delta, x):
        dx = delta
        xdim = getattr(x, "ndim", 0)
        xshape = getattr(x, "shape", ())
        if delta.ndim != xdim:
            dx = dx.sum(axis=tuple(range(dx.ndim - xdim)))
            if isinstance(dx, np.number):
                dx = np.array(dx)
        axis = tuple(i for i, len_ in enumerate(xshape) if len_ == 1)
        if axis:
            dx = dx.sum(axis=axis, keepdims=True)
        return dx


def broadcast_to(x, shape):
    """
    Broadcast a tensor to an new shape
    """
    return BroadcastTo(shape).forward(x)


def broadcast(args):
    """
    broadcast list of tensors to make them have the same shape

    Parameters
    ----------
    args : list
        list of Tensor to be aligned

    Returns
    -------
    list
        list of Tensor whose shapes are aligned
    """
    shape = np.broadcast(*(arg.value for arg in args)).shape
    for i, arg in enumerate(args):
        if arg.shape != shape:
            args[i] = BroadcastTo(shape).forward(arg)
    return args
