import host
import threading
host1=host.HOST(config_pt='./config.ini',host_send='udpport_1', host_recv='udpport_2')

host_receiver=threading.Thread(target=host1.RecvThread, args=('./copy2.txt',))
host_receiver.start()
host_sender = threading.Thread(target=host1.SendThread, args=('./test1.txt',))
host_sender.start()
host_receiver.join()
host_sender.join()