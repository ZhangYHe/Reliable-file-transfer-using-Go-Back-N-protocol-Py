import configparser
import socket
import time
import random
import math


'''
PDU帧结构
seq 
ack                       
is_data  (ack=0,data=1)         1B
data
checksum                        2B
'''


class HOST:
    def __init__(self, config_pt, host_send='udpport_1', host_recv='udpport_2'):
        print(" -> init : read config file ", config_pt)
        # 读取配置文件
        file = config_pt
        # 创建配置文件对象
        con = configparser.ConfigParser()
        # 读取文件
        con.read(file, encoding='utf-8')
        # 获取特定section 返回结果为元组
        general_items = con.items('general')
        # 将元组通过dict方法转换为字典
        general_items = dict(general_items)

        # 获取配置文件参数
        self.DataSize = eval(general_items['datasize'])
        self.ErrorRate = eval(general_items['errorrate'])
        self.LostRate = eval(general_items['lostrate'])
        self.SWSize = eval(general_items['swsize'])
        self.InitSeqNo = eval(general_items['initseqno'])
        self.Timeout = eval(general_items['timeout'])
        self.UDPPort_send = eval(general_items[host_send])
        self.UDPPort_recv = eval(general_items[host_recv])

        # 配置发送方与接收方信息
        self.host_send = host_send
        self.host_recv = host_recv

        # PDU数据部分长度应小于4KB
        if self.DataSize > 4096:
            print("Error : DataSize > 4KB ")
            return

        # 初始化socket
        print(" -> init : socket init ")
        # 根据host名称配置发送地址与接收地址
        self.SendAddr = ('localhost', self.UDPPort_send)
        self.RecvAddr = ('localhost', self.UDPPort_recv)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.SendAddr)
        # 设置socket超时时长为5s
        self.sock.settimeout(5)

        # 打开log文件，准备写入日志记录
        self.log_file = open(self.host_send + '_log.csv', 'a', encoding='utf-8')

        # 最大序号为窗口尺寸 +1
        # 0-MaxSeq-1
        self.MaxSeq = self.SWSize + 1
        self.SeqByteNum = math.ceil(math.ceil(math.log(self.SWSize + 1, 2)) / 8)
        if self.InitSeqNo > self.MaxSeq:
            print("Error : InitSeqNo > MaxSeqNo ")
            return

        # 存储待发送的数据
        self.send_packets = []
        # 0-MaxSeq-1
        # pdu_exp表示期望接收的pdu序号
        self.pdu_exp = self.InitSeqNo

        # 0-packet_num-1
        # pdu_to_send表示下一个待发送的pdu序号
        self.pdu_to_send = 0

        # 0-MaxSeq-1
        # pdu_recv表示接收到的pdu序号
        self.pdu_recv = 0

        # 0 1 2分别表示不同的发送和接收状态
        self.send_pdu_status_flag = 0
        self.recv_pdu_status_flag = 0

        # 0-MaxSeq-1
        # ackedNo表示最新接收到的ACK帧序号
        self.ackedNo = -1

        # 0-packet_num-1
        # SWBeginNo表示发送窗口起始的pdu序号
        self.SWBeginNo = 0

        self.is_sending_data = False
        self.end_recving = False

        # TImer_start存储计时器开始时间
        self.Timer_start = -1
        # TImer_stop_flag为计时器停止标志
        self.Timer_stop_flag = -1
        self.Timer_duration = self.Timeout / 1000


    def SendThread(self, send_fpth):
        print(" -> SendThread : sendthread init ")
        # 记录发送进程开始时间
        Send_start_time = time.time()

        self.is_sending_data = True

        # 读取待发送的文件，存入列表中
        send_file = open(send_fpth, 'rb')
        self.send_packets = []

        # 按照DataSize长度读取待发送的文件
        packet_data = send_file.read(self.DataSize)
        self.send_packets.append(packet_data)
        while packet_data:
            self.send_packets.append(packet_data)
            packet_data = send_file.read(self.DataSize)

        # 获取待发送的pdu数据个数
        send_packets_num = len(self.send_packets)
        # print(send_packets_num)
        print(" -> SendThread : is sending ", send_packets_num, " packets ")

        # 获取窗口尺寸，防止窗口越界
        WindowLen = min(self.SWSize, send_packets_num - self.SWBeginNo)
        # 遍历发送send_packets
        while self.SWBeginNo < send_packets_num:
            # 发送当前窗口内全部pdu
            while self.pdu_to_send < self.SWBeginNo + WindowLen:
                send_data = self.generateSendData(self.pdu_to_send)
                # 随机生成丢失错误
                if random.random() < (1 / self.LostRate):
                    print(" -> SendThread : pdu lost   ", time.ctime(), self.getSeqNo(self.pdu_to_send),
                          self.pdu_to_send, self.SWBeginNo)
                    # 将丢失信息写入日志文件中
                    log_str = self.getSendLog('lost')
                    self.log_file.write(log_str)
                    self.pdu_to_send += 1
                    # 动态更新窗口尺寸，防止越界
                    WindowLen = min(self.SWSize, send_packets_num - self.SWBeginNo)
                    continue
                # 随机生成数据错误
                elif random.random() < (1 / self.ErrorRate):
                    print(" -> SendThread : pdu error  ", time.ctime(), self.getSeqNo(self.pdu_to_send),
                          self.pdu_to_send, self.SWBeginNo)
                    # 将错误信息写入日志文件中
                    log_str = self.getSendLog('error')
                    self.log_file.write(log_str)
                    # 发送错误数据
                    send_data += b'\xff'
                    self.sock.sendto(send_data, self.RecvAddr)
                # 没有错误发生，发送正确的pdu帧
                else:
                    self.sock.sendto(send_data, self.RecvAddr)
                    # 将发送信息写入日志文件中
                    log_str = self.getSendLog()
                    self.log_file.write(log_str)
                    print(" -> SendThread : Send a pdu ", time.ctime(), self.getSeqNo(self.pdu_to_send),
                          self.pdu_to_send, self.SWBeginNo)
                self.pdu_to_send += 1
                # 动态更新窗口尺寸，防止越界
                WindowLen = min(self.SWSize, send_packets_num - self.SWBeginNo)

                if self.send_pdu_status_flag == 1:
                    self.send_pdu_status_flag = 2

            self.send_pdu_status_flag = 0

            # 如果未开始计时，开启计时器
            if self.Timer_start == self.Timer_stop_flag:
                self.Timer_start = time.time()

            # 计时器正在运行且时长小于TO，循环等待
            while self.Timer_start != self.Timer_stop_flag and (time.time() - self.Timer_start) < self.Timer_duration:
                time.sleep(0.5)

            # 计时器正在运行且超时
            if self.Timer_start != self.Timer_stop_flag and (time.time() - self.Timer_start) >= self.Timer_duration:
                print(" -> SendThread : Timeout    ", time.ctime())
                # 终止计时器
                self.Timer_start = self.Timer_stop_flag
                # 重新发送窗口内全部pdu
                self.pdu_to_send = self.SWBeginNo
                self.send_pdu_status_flag = 1
                # 将超时信息写入日志文件中
                log_str = 'Send,' + time.ctime() + ',Time out\n'
                self.log_file.write(log_str)
            # 计时器没有超时
            else:
                print(" -> SendThread : Accept ACK ", time.ctime(), self.ackedNo)
                # 动态更新窗口尺寸，防止越界
                WindowLen = min(self.SWSize, send_packets_num - self.SWBeginNo)
                self.send_pdu_status_flag = 0

        # 全部pdu均已发送，发送空帧表示结束
        self.is_sending_data = False
        self.sock.sendto(b'', self.RecvAddr)

        # 获取发送进程运行时长
        Send_end_time = time.time()
        Send_total_time = Send_end_time - Send_start_time

        # 将发送进程信息写入日志文件中
        print(" -> SendThread : Send all data , finished ", time.ctime())
        self.log_file.write("Send Finished," + str(send_packets_num) + ',' + str(Send_total_time) + ',\n')
        # self.log_file.close()
        send_file.close()


    def RecvThread(self, recv_fpth):
        print(" -> RecvThread : receivethread init ")
        # 获取接收进程起始时间
        Recv_start_time = time.time()
        self.end_recving = False

        # 打开接收文件，准备写入数据
        recv_file = open(recv_fpth, 'wb')

        # 循环运行，接收pdu帧
        while True:
            # 当前主机没有发送数据且已经接收全部pdu，退出循环
            if self.is_sending_data == False and self.end_recving == True:
                print(" -> RecvThread : close RecvThread ", time.ctime())
                # 获取接收进程运行时长
                Recv_end_time = time.time()
                Recv_total_time = Recv_end_time - Recv_start_time
                # 将接收进程信息写入日志文件中
                self.log_file.write("Receive Finished," + str(Recv_total_time) + '\n')
                # self.log_file.close()
                break

            # 接收pdu帧
            pdu_packet, addr = self.sock.recvfrom(self.UDPPort_recv)

            # 若为空帧，则表示发送进程结束，已接收全部数据
            if pdu_packet == b'':
                print(" -> RecvThread : Receive all data , finished ", time.ctime())
                self.end_recving = True
                recv_file.close()
                continue

            # 拆分pdu帧
            seqNo_bytes, ackNo_bytes, is_data_bytes, data_bytes, crc_bytes = self.splitData(pdu_packet)

            # CRC校验错误，发生数据错误
            if self.CRC_CCITT_Check(pdu_packet) == False:
                # 更新接收状态
                self.recv_pdu_status_flag = 1
                print(" -> RecvThread : pdu error     ", time.ctime())
                # 将数据错误信息写入日志文件中
                log_str = self.getRecvLog('data error')
                self.log_file.write(log_str)
                self.recv_pdu_status_flag = 0
                continue

            # is_data表示当前pdu帧中是否携带数据
            is_data = is_data_bytes

            # 将bytes型数据转换为int型序号
            ackNo = int.from_bytes(ackNo_bytes, byteorder='big', signed=False)
            seqNo = int.from_bytes(seqNo_bytes, byteorder='big', signed=False)

            # 更新接收信息
            self.ackedNo = ackNo
            self.pdu_recv = seqNo


            # 发送进程正在发送数据
            if self.is_sending_data == True:
                # 根据ack序号动态更新发送窗口起始位置
                if self.SWCheck(self.getSeqNo(self.SWBeginNo), ackNo, self.getSeqNo(self.pdu_to_send)):
                    while self.SWCheck(self.getSeqNo(self.SWBeginNo), ackNo, self.getSeqNo(self.pdu_to_send)):
                        self.SWBeginNo += 1
                    # 终止发送计时器
                    self.Timer_start = self.Timer_stop_flag
                    self.send_pdu_status_flag = 0
                # if self.SWCheck(self.getSeqNo(self.SWBeginNo), self.ackedNo,self.getSeqNo(self.pdu_to_send)):
                #     while self.SWCheck(self.getSeqNo(self.SWBeginNo), self.ackedNo, self.getSeqNo(self.pdu_to_send)):
                #         self.SWBeginNo += 1
                #     self.Timer_start = self.Timer_stop_flag


                # 如果收到的pdu帧有数据
                if is_data == 1:
                    # 收到的pdu帧与期望的序号一致
                    if self.pdu_recv == self.pdu_exp:
                    # if seqNo == self.pdu_exp:
                        print(" -> RecvThread : receive a pdu ", time.ctime(), seqNo, self.pdu_exp)
                        # 将odu中数据写入文件
                        recv_file.write(data_bytes)
                        # 将接收信息写入日志文件中
                        log_str = self.getRecvLog('normal')
                        self.log_file.write(log_str)
                        # 动态更新pdu_exp序号
                        self.pdu_exp = (self.pdu_exp + 1) % self.MaxSeq
                    # 收到的pdu帧与期望的序号不一致
                    else:
                        # 将错误信息写入日志文件中
                        self.recv_pdu_status_flag = 2
                        print(" -> RecvThread : Number error  ", time.ctime(), seqNo, self.pdu_exp)
                        log_str = self.getRecvLog("Number error")
                        self.log_file.write(log_str)
                        self.recv_pdu_status_flag = 0
                # 收到ACK
                # else:
                #     if self.pdu_recv == self.pdu_exp:
                #         print(" -> RecvThread : receive a ACK ", time.ctime())
                #         # if self.SWCheck(self.getSeqNo(self.SWBeginNo), self.ackedNo,
                #         #                 self.getSeqNo(self.pdu_to_send)):
                #         #     while self.SWCheck(self.getSeqNo(self.SWBeginNo), self.ackedNo \
                #         #             , self.getSeqNo(self.pdu_to_send)):
                #         #         self.SWBeginNo += 1
                #         #     self.Timer_start = self.Timer_stop_flag
                #         log_str = self.getRecvLog("normal")
                #         self.log_file.write(log_str)
                #         self.pdu_exp = (self.pdu_exp + 1) % self.MaxSeq
                #     else:
                #         self.recv_pdu_status_flag = 2
                #         print(" -> RecvThread : Number error ", time.ctime())
                #         log_str = self.getRecvLog("Number error")
                #         self.log_file.write(log_str)
                #         self.recv_pdu_status_flag = 0

            # 当前主机发送进程不发数据，只接收数据，需要发送ACK
            else:
                # 收到的pdu帧与期望的序号一致
                if self.pdu_recv == self.pdu_exp:
                # if seqNo == self.pdu_exp:
                    # 将接收到的数据写入文件中
                    print(" -> RecvThread : receive a pdu ", time.ctime(), seqNo, self.pdu_exp)
                    recv_file.write(data_bytes)
                    # 将接收信息写入日志文件中
                    log_str = self.getRecvLog("normal")
                    self.log_file.write(log_str)
                    # 动态更新pdu_exp
                    self.pdu_exp = (self.pdu_exp + 1) % self.MaxSeq
                    # 发送ack帧
                    ack_data = self.generateACK(self.pdu_exp)
                    self.sock.sendto(ack_data, self.RecvAddr)
                # 收到的pdu帧与期望的序号不一致
                else:
                    # 将错误信息写入日志文件中
                    self.recv_pdu_status_flag = 2
                    print(" -> RecvThread : Number error  ", time.ctime(), seqNo, self.pdu_exp)
                    log_str = self.getRecvLog("Number error")
                    self.log_file.write(log_str)
                    self.recv_pdu_status_flag = 0
                    # 发送ack帧
                    ack_data = self.generateACK(self.pdu_exp)
                    self.sock.sendto(ack_data, self.RecvAddr)

        print(" -> RecvThread : Receive all data , finished ", time.ctime())
        recv_file.close()


    # 生成待发送的pdu帧
    def generateSendData(self, pduNo):
        # seqNo，ackNo所占字节数与窗口尺寸有关
        # 生成pdu序号
        seqNo = self.getSeqNo(pduNo)
        seqNo_bytes = seqNo.to_bytes(self.SeqByteNum, byteorder='big', signed=False)
        # ackNo为当前接收到的最后一个pdu帧序号
        ackNo = (self.pdu_exp + self.MaxSeq - 1) % self.MaxSeq
        ackNo_bytes = ackNo.to_bytes(self.SeqByteNum, byteorder='big', signed=False)
        # 该pdu帧中有数据
        is_data = 1
        is_data_bytes = is_data.to_bytes(1, byteorder='big', signed=False)
        data_bytes = self.send_packets[pduNo]

        pdu_data = seqNo_bytes + ackNo_bytes + is_data_bytes + data_bytes

        # 生成crc校验码
        crc_bytes_list = self.genCRC_CCITT_Code(pdu_data)
        for item in crc_bytes_list:
            pdu_data += item

        # 返回待发送的pdu帧
        return pdu_data


    # 生成ACK帧
    def generateACK(self, ackNo):
        # seqNo，ackNo所占字节数与窗口尺寸有关
        # ACK帧没有数据，seqNo为0
        seqNo = 0
        seqNo_bytes = seqNo.to_bytes(self.SeqByteNum, byteorder='big', signed=False)
        # ackNo为当前接收到的最后一个pdu帧序号
        ack = (ackNo + self.MaxSeq - 1) % self.MaxSeq
        ackNo_bytes = ack.to_bytes(self.SeqByteNum, byteorder='big', signed=False)
        # ACK帧没有数据，is_data为0
        is_data = 0
        is_data_bytes = is_data.to_bytes(1, byteorder='big', signed=False)
        # 数据部分为空
        data_bytes = b''

        pdu_data = seqNo_bytes + ackNo_bytes + is_data_bytes + data_bytes

        # 生成crc校验码
        crc_bytes_list = self.genCRC_CCITT_Code(pdu_data)
        for item in crc_bytes_list:
            pdu_data += item

        # 返回待发送的pdu帧
        return pdu_data


    # 拆分收到的pdu帧
    def splitData(self, data):
        # seqNo，ackNo所占字节数与窗口尺寸有关
        seqNo_bytes = data[0:self.SeqByteNum]
        ackNo_bytes = data[self.SeqByteNum:self.SeqByteNum * 2]

        # is_data_bytes 1 为数据帧
        # is_data_bytes 0 为ACK
        is_data_bytes = data[self.SeqByteNum * 2]
        data_bytes = data[self.SeqByteNum * 2 + 1:-2]

        # crc校验码占2字节
        crc_bytes = data[-2:]

        return seqNo_bytes, ackNo_bytes, is_data_bytes, data_bytes, crc_bytes


    # 根据ack序号检查是否在当前窗口中
    def SWCheck(self, beginNo, ackNo, pdu_to_sendNo):
        # ack序号共有三种情况
        # 从左至右分别为 beginNo, ackNo, pdu_to_sendNo
        # 1 2 3
        if beginNo <= ackNo < pdu_to_sendNo:
            return True
        # 6 7 0
        elif pdu_to_sendNo < beginNo <= ackNo:
            return True
        # 7 0 1
        elif ackNo < pdu_to_sendNo < beginNo:
            return True
        else:
            return False


    # 按照CRC-CCITT标准生成CRC校验码
    def genCRC_CCITT_Code(self, data, debug=False):

        crc_to_send = list()
        crc = 0xFFFF

        # 计算CRC校验码
        for b in data:
            crc ^= b
            for _ in range(0, 8):
                bcarry = crc & 0x0001
                crc >>= 1
                if bcarry:
                    crc ^= 0xa001

        if crc > 0xff:
            msb = crc >> 0x08 & 0xff
            lsb = crc & 0xff
            crc_to_send = [lsb, msb]
        else:
            crc_to_send = [crc]

        for i in range(len(crc_to_send)):
            crc_to_send[i] = crc_to_send[i].to_bytes(1, byteorder='big', signed=False)

        if debug:
            print(f'Generated CRC: {crc}')
            print(f'Converted CRC to hex: {hex(crc)}')
            print(f'CRC to send to receiver: {crc_to_send}')

        return crc_to_send


    # 将CRC校验码添加在帧尾
    def genCRC_CCITT(self, data, debug=False):
        data.extend(genCRC_CCITT_Code(data))
        if debug:
            print(f'Complete packet: {data}')

        return data


    # 检查数据是否出错
    def CRC_CCITT_Check(self, data, debug=False):
        # 根据pdu帧生成CRC校验码
        remainder = self.genCRC_CCITT_Code(data)
        if debug:
            print(f'Data packet: {data_packet} -> Remainder: {remainder}')

        # 若余数为0则没有出错，反之则出错
        for i in range(len(remainder)):
            remainder[i] = int.from_bytes(remainder[i], byteorder='big', signed=False)
        if sum(remainder) == 0:
            return True
        else:
            return False


    # 根据起始序号、最大序号生成pdu帧序号
    def getSeqNo(self, packetNo):
        return (packetNo + self.InitSeqNo) % self.MaxSeq


    # 根据状态标志位生成发送状态
    def getSendPduStatus(self, flag):
        if flag == 0:
            return "New"
        elif flag == 1:
            return "TO"
        elif flag == 2:
            return "Rt"
        else:
            return "Error"

    # 根据状态标志位生成接收状态
    def getRecvPduStatus(self, flag):
        if flag == 0:
            return "OK"
        elif flag == 1:
            return "DataErr"
        elif flag == 2:
            return "NoErr"
        else:
            return "Error"


    # 生成csv格式的发送日志信息字符串
    def getSendLog(self, type='normal'):
        log_str = 'Send,' + time.ctime() + ',pdu_to_send=' + str(self.pdu_to_send) + ',status=' \
                  + self.getSendPduStatus(self.send_pdu_status_flag) + ',pdu_No=' \
                  + str(self.getSeqNo(self.pdu_to_send)) + ',pdu_Seq=' + str(self.pdu_to_send) \
                  + ',ackedNo=' + str(self.ackedNo) + ',SWBegin_No=' + str(self.SWBeginNo)
        if type == "lost":
            log_str += ',lost\n'
            return log_str
        elif type == "error":
            log_str += ',error\n'
            return log_str
        elif type == "normal":
            log_str += '\n'
            return log_str
        else:
            print("gerSendLog Error")
            return

    # 生成csv格式的接收日志信息字符串
    def getRecvLog(self, type='normal'):
        log_str = 'Receive,' + time.ctime() + ',pdu_exp=' + str(self.pdu_exp) + ',pdu_recv=' \
                  + str(self.pdu_recv) + ',status=' + self.getRecvPduStatus(self.recv_pdu_status_flag)
        if type == "data error":
            log_str += ',data error\n'
            return log_str
        elif type == "normal":
            log_str += '\n'
            return log_str
        elif type == "Number error":
            log_str += ',Number error\n'
            return log_str
        else:
            print("gerSendLog Error")
            return


if __name__ == '__main__':
    pass
    # host1 = HOST("config.ini", 'udpport_1', 'udpport_2')
    # host1.test()
    # host1.SendThread("sendfile.txt")

    # host1 = HOST("config.ini")
    # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # sock.bind(('localhost', 40951))
    # sock.settimeout(3)
    # while True:
    #     s="11111"
    #     sock.sendto(s.encode(),('localhost', 40952))
    # udt.send(s, sock, ('localhost', 40952))
