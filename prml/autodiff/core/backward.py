import numpy as np

from prml.autodiff.core.array import Array
from prml.autodiff.core.config import config


class BackPropTaskManager(object):

    def __init__(self):
        self._tasks = set()

    def __len__(self):
        return len(self._tasks)

    def __contains__(self, task: Array):
        return task in self._tasks

    def add_task(self, task: Array):
        if not isinstance(task, Array):
            raise TypeError
        self._tasks.add(task)

    def pop_next_task(self):
        task = max(self._tasks, key=lambda x: x._depth)
        self._tasks.discard(task)
        return task


def backward(array: Array, grad=None):
    if grad is None:
        grad = np.ones_like(array.value).astype(config.dtype)
    assert(grad.shape == array.value.shape)
    array._accumulate_gradient_from_child(grad)
    backprop_taskmanager = BackPropTaskManager()
    backprop_taskmanager.add_task(array)
    while len(backprop_taskmanager):
        task = backprop_taskmanager.pop_next_task()
        if task._parent is not None:
            task._parent.backward(task._gradtmp, backprop_taskmanager)
        task.update_grad(task._gradtmp)
        task.gradtmp = None
