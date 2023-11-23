# Reliable-transfer-using-Go-Back-N-protocol-Py

采用GBN（Go-Back-N）协议实现的可靠的文件传输 .  Reliable file transfer using Go-Back-N protocol.

北京理工大学 计算机网络 课程作业 Project 1

100071011 Computer Networks 2022-2023-2

Project-1: Reliable File Transfer using Go-Back-N protocol

## 1. **Requirement Analysis**

Understanding and analysis of project requirements.

Understanding how and why GBN can be used to transfer file reliably.

Learning the specific matter process of GBN algorithm.

Understand the implementation details of the GBN algorithm.

Learning how to use multi-threaded approach to transfer file.

Learning how to use the UDP Socket API.

Understanding the PDU structure.

Understanding the CRC-CCITT standard.

## 2. **Design**

### (1) Frame structure

The frame structure consists of pdu serial number, ack serial number, flag bit, data, crc checksum. The number of bytes of the pdu number and the ack number is determined by the window size. The flag bit and crc checksum occupy 1 byte and 2 bytes respectively. The 0 and 1 in the flag bit represent whether it is an ack frame or a data frame, respectively.

### (2) Sliding windows

Sliding window protocols allow multiple frames to be in transit. Transmitter can send up to W frames without ACK. Sequence number bounded by size of field sequence, where frames are numbered modulo 2^n (0 ~ 2^n-1). Sender maintains a set of sequence numbers

corresponding to frames it is permitted to send, called the sending window. When a packet arrives, next highest sequence number assigned and upper edge of window advanced by 1. When an acknowledgement arrives, the lower edge of window advanced by 1.

### (3) Sequence spaces

The window size determines the maximum serial number and the number of bytes occupied by the serial number.

MS=SW+1

N=⌊log2SW+1/8⌋

In the above equation, MS stands for Maximum Serial Number and N represents the number of bytes occupied by the serial number.

### (4) Acknowledgment rules

The receiver send ack frame. Continuously update pdu\_exp and ackedNo. If the pdu\_exp serial number is equal to the received data frame serial number, the data is received and the pdu\_exp serial number is updated. If the receiver's pdu\_exp sequence number is not equal to the received data frame sequence number, the previous ack frame is sent. The sender receives the ack frame, updates the window start position according to the ack number, and clears the timer. If the timer times out and no ack frame is received, resend the data frame.

### (5) Possible errors and simulations

Given the frequency of frame loss and data errors in the configuration file, where n represents an error that occurs every n frames. Randomly generate a random number between 0 and 1. If it is less than the probability of error occurrence, an error will be generated.

### (6) Logging

Use CSV files to record the communication status of sending and receiving. The sending process writes information such as the sending time, PDU serial number, sending status, acked serial number, and window start serial number to the CSV file. The receiving process writes information such as receiving time, pduexp, current received pdu serial number, and receiving status to a file.

### (7) Configuration file

Using an ini file to record configuration information. Use the configparser library to read the ini file and store the configuration information in dict. Configuration information can be directly read during program operation.

### (8) Multi-thread

Create separate sending and receiving threads to achieve concurrent file transfer and full duplex communication. This allows multiple hosts to simultaneously send files to each other.

### (9) CRC-CCITT standard

CRC-CCITT standard using the polynomial of x^16+x^12+x^5+1. Sender and receiver agree on the “generator” of the code. Append a “CRC” to the end of the message. If G(x) is of degree r, then append r 0s to the end of the m messsage bits. Subtract the remainder from x^rM(x) modulo 2, The result is the checksummed frame to be transmitted T(x). The receiver check if the received data is divisible by G(x). If the remainder is 0 then there is no error, otherwise an error occurs.

### (10) Log analysis

Read the CSV file of the log and perform statistical analysis on the communication status record data. Analyze the impact of data size, window size, PDU error rate, PDU loss rate, and other factors on communication efficiency from multiple dimensions. Calculate the total number of PDUs divided into files, total communication times, timeout times, number of PDUs retransmitted, and total time spent.

## 3. **Development and Implementation**

Languages: Python 3.9

Libraries: seaborn 0.11.2, matplotlib 3.4.3, numpy 1.21.2, pandas 1.3.5, csv, configparser, socket, threading, time, random, math.

OS: windows 10.

IDE: PyCharm

## 4. **Development and Implementation**

### 4.1 Generate PDU

```python
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

```

### 4.2 CRC-CCITT

```python
1. # 按照CRC-CCITT标准生成CRC校验码
2.     def genCRC_CCITT_Code(self, data, debug=False):
3. 
4.         crc_to_send = list()
5.         crc = 0xFFFF
6. 
7.         # 计算CRC校验码
8.         for b in data:
9.             crc ^= b
10.             for _ in range(0, 8):
11.                 bcarry = crc & 0x0001
12.                 crc >>= 1
13.                 if bcarry:
14.                     crc ^= 0xa001
15. 
16.         if crc > 0xff:
17.             msb = crc >> 0x08 & 0xff
18.             lsb = crc & 0xff
19.             crc_to_send = [lsb, msb]
20.         else:
21.             crc_to_send = [crc]
22. 
23.         for i in range(len(crc_to_send)):
24.             crc_to_send[i] = crc_to_send[i].to_bytes(1, byteorder='big', signed=False)
25. 
26.         if debug:
27.             print(f'Generated CRC: {crc}')
28.             print(f'Converted CRC to hex: {hex(crc)}')
29.             print(f'CRC to send to receiver: {crc_to_send}')
30. 
31.         return crc_to_send

```

### 4.3 Multi-thread

```python
1. import host
2. import threading
3. host1=host.HOST(config_pt='./config.ini',host_send='udpport_1', host_recv='udpport_2')
4. 
5. host_receiver=threading.Thread(target=host1.RecvThread, args=('./copy2.txt',))
6. host_receiver.start()
7. host_sender = threading.Thread(target=host1.SendThread, args=('./test1.txt',))
8. host_sender.start()
9. host_receiver.join()
10. host_sender.join()

```

## 4. **System Deployment, Startup, and Use**

Create two Python files separately, representing different hosts. When using, simply write “import host” in the file, create the corresponding class, and pass in parameters such as the configuration file to start running. Host_Send and host_ Recv corresponds to the names of two hosts in the configuration file. The parameters of the sending process and the receiving process are the file path to be sent and the receiving file path, respectively. Here is a sample code. Two host log files will be created in the same level directory.

```python
1. import host
2. import threading
3. host1=host.HOST(config_pt='./config.ini',host_send='udpport_1', host_recv='udpport_2')
4. 
5. host_receiver=threading.Thread(target=host1.RecvThread, args=('./copy2.txt',))
6. host_receiver.start()
7. host_sender = threading.Thread(target=host1.SendThread, args=('./test1.txt',))
8. host_sender.start()
9. host_receiver.join()
10. host_sender.join()

```
