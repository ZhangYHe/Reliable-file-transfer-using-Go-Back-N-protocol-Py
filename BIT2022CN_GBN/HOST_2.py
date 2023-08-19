import host
import threading

host2=host.HOST(config_pt='./config.ini',host_send='udpport_2', host_recv='udpport_1')

host2.RecvThread('./copy_from_HOST_1.txt')