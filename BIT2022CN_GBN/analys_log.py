import csv
import configparser
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


class AnalysLog():
    def __init__(self, log_pt, config_pt='config.ini'):
        self.log_pt = log_pt
        file = config_pt
        # 创建配置文件对象
        con = configparser.ConfigParser()
        # 读取文件
        con.read(file, encoding='utf-8')
        self.general_items = con.items('general')
        self.general_items = dict(self.general_items)

        print("-------------config---------------")
        for key, value in self.general_items.items():
            print("{:<10} = {:>8}".format(key, value))
        print("----------------------------------")

        self.file_reader = csv.reader(open(log_pt, "r", encoding='utf8', newline=''))

        self.LogData = dict()

        self.LogData['pdu_num'] = 0
        self.LogData['SendNum'] = 0
        self.LogData['RecvNum'] = 0
        self.LogData['TotalNum'] = 0
        self.LogData['TONum'] = 0
        self.LogData['RTNum'] = 0
        self.LogData['NoErrNum'] = 0
        self.LogData['DataErrNum'] = 0
        self.LogData['SendTotalTime'] = ''
        self.LogData['RecvTotalTime'] = ''

    def getLogData(self, wirteHM=True, HotMap_pt='HotMap.csv'):
        for row in self.file_reader:
            row_list = list(row)

            if row[0] == "Send":
                self.LogData['SendNum'] += 1

                if row[-1] == 'Time out':
                    self.LogData['TONum'] += 1
                if len(row) > 3:
                    if row[3] != "status=New":
                        self.LogData['RTNum'] += 1

            elif row[0] == "Receive":
                self.LogData['RecvNum'] += 1
                if row[-1] == "data error":
                    self.LogData['DataErrNum'] += 1
                if row[-1] == "Number error":
                    self.LogData['NoErrNum'] += 1

            elif row[0] == "Receive Finished":
                self.LogData['RecvTotalTime'] = row[1]

            elif row[0] == "Send Finished":
                self.LogData['pdu_num'] = row[1]
                self.LogData['SendTotalTime'] = row[2]
        self.LogData['TotalNum'] = self.LogData['SendNum'] + self.LogData['RecvNum']
        self.LogData['TO Rate'] = self.LogData['TONum'] / self.LogData['TotalNum']
        self.LogData['RT Rate'] = self.LogData['RTNum'] / self.LogData['TotalNum']
        self.LogData['Efficiency'] = eval(self.LogData['pdu_num']) / self.LogData['TotalNum']
        # self.LogData['NoErr Rate'] = self.LogData['NoErrNum'] / self.LogData['TotalNum']
        # self.LogData['DaErr Rate'] = self.LogData['DataErrNum'] / self.LogData['TotalNum']

        print("---{}---Log data---".format(self.log_pt))
        for key, value in self.LogData.items():
            print("{:<10} = {:>8}".format(key, value))
        print("----------------------------------")

        # 将结果写入csv文件中
        if wirteHM:
            HMfile = open(HotMap_pt, 'a', encoding='utf-8')
            HMstr = self.general_items['swsize'] + ',' + self.general_items['timeout'] + ',' + str(
                self.LogData['Efficiency']) + ',' + self.general_items['datasize'] + ',' + self.general_items[
                        'errorrate'] + ',' + self.general_items['lostrate'] + ',' + self.LogData[
                        'SendTotalTime'] + '\n'
            HMfile.write(HMstr)
            HMfile.close()

    def DrawHotMap(self, file_pt='HotMap.csv'):
        f = pd.read_csv(file_pt)
        f.head()

        #pivot = f.pivot(index='SWSize', columns='Timeout', values='Efficiency')
        pivot = f.pivot(index='SWSize', columns='Timeout', values='SendTime')

        sns.heatmap(pivot, annot=True, fmt="f", linewidths=1.6, cmap="RdBu_r")
        #"RdBu_r""RdPu_r"
        # sns.heatmap(pivot,cmap= "RdBu_r")

        plt.show()


if __name__ == '__main__':
    analys_1 = AnalysLog(log_pt="udpport_1_log.csv")
    analys_2 = AnalysLog(log_pt="udpport_2_log.csv")

    #analys_1.getLogData()
    analys_1.DrawHotMap()

    analys_2.getLogData(wirteHM=False)
