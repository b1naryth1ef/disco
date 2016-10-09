from .memory import MemoryBackend
from .disk import DiskBackend


BACKENDS = {
    'memory': MemoryBackend,
    'disk': DiskBackend,
}
