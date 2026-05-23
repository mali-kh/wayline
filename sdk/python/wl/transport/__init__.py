"""
Transport implementations for Wayline task communication.

Currently supported:
    zmq://  — ZeroMQ PUSH/PULL over TCP (default for remote tasks)

Planned:
    shm://  — shared memory via POSIX shm (same-node optimization)
"""
