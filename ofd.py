#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import os
import json
import config
import requests
import datetime
from bs4 import BeautifulSoup


class OFDProvider:
    # заводской номер фискального накопителя
    # fiscalDriveId
    # fn
    # ФН
    fiscal_drive_id = None
    # номер фискального документа
    # fiscalDocumentNumber
    # i
    # ФД
    fiscal_document_number = None
    # номер ФПД
    # фискальный признак документа
    # fp
    # ФП
    fiscal_id = None
    # регистрационный номер ККТ
    kkt = None
    # время покупки
    time = None
    # сумма чека
    raw_sum = 0
    # номер чека
    number = 0
    # идентификатор чека на сервере
    receipt_id = ""
    # данные чека
    receipt_data = None
    # опция для возможности повторной отправки данных уже сохраненного чека
    resend = False

    # регулярное выражение для проверки соответствия формату текста QR
    ofd_type1_match_regexp = "t=([\dT]+)&s=([\d\.]+)&fn=(\d+)&i=(\d+)&fp=(\d+)&n=(\d+)"

    def __init__(self, resend):
        self.resend = resend

    def load(self, data):
        for key in data:
            setattr(self, key, data[key])

    def parse_data(self, fields):
        time = datetime.datetime.strptime(fields[0], "%Y%m%dT%H%M%S")
        drebtime = time.strftime("%Y-%m-%d %H:%M:%S")

        return {
            "raw_time": fields[0],
            "time": time,
            "dreb_time": drebtime,
            "raw_sum": fields[1],
            "fiscal_drive_id": fields[2],
            "fiscal_document_number": fields[3],
            "fiscal_id": fields[4],
            "number": fields[5]
        }

    # определение ОФД по данным чека и запросами
    def detect(self, text):
        ofd_type1_match = re.match(self.ofd_type1_match_regexp, text)
        # проверка чека по обычному на данный момент содержанию QR
        if ofd_type1_match:
            # получаем данные чека
            data = self.parse_data(ofd_type1_match.groups())

            print("Ticket {3} at {0} with sum {1}, FPD {4}, fiscal drive {2} (n={5})".format(
                data['time'], data['raw_sum'], data['fiscal_drive_id'], data['fiscal_document_number'], data['fiscal_id'], data['number']))

            # для списка известных провайдеров
            for provider in [OFD1, PlatformaOFD]:
                # проверяем что данные удовлетворяют требованиям ОФД
                if provider(self.resend).is_suitable(data):
                    # инициализируем и загружаем данные
                    ofd = provider(self.resend)
                    ofd.load(data)
                    # если поиск успешен, то возвращаем инстанс чека этого ОФД
                    if ofd.search():
                        return ofd

        elif text.startswith("http://check.egais.ru"):
            print("This is an EGAIS receipt without sum!")
            return False
        # добавить распознавание ЕГАИС
        else:
            print("No match with known OFD in content!")
            return False

    # имя файла для сохранения контента чека из ОФД
    def get_receipt_file_name(self):
        filename = self.raw_time + "_" + self.fiscal_id + \
            "_" + self.fiscal_drive_id + ".txt"
        return os.path.join(config.receipt_dir, filename)

    # имя файла для сохранения файла загрузки в Дребеденьги
    def get_csv_file_name(self):
        filename = self.raw_time + "_" + self.fiscal_id + \
            "_" + self.fiscal_drive_id + ".csv"
        return os.path.join(config.report_dir, filename)


class PlatformaOFD(OFDProvider):
    url_receipt_get = "https://lk.platformaofd.ru/web/noauth/cheque?fn={}&fp={}"

    def is_suitable(self, data):
        return data['fiscal_drive_id'] and data['fiscal_id']

    def search(self):
        print("Search in Platforma OFD...")
        request = requests.get(self.url_receipt_get.format(
            self.fiscal_drive_id, self.fiscal_id))
        if "Чек не найден" in request.content:
            print("Not found!")
            return False
        else:
            self.receipt_data = request.content
            filename = self.get_receipt_file_name()

            if not os.path.exists(filename):
                with open(filename, 'w') as outfile:
                    outfile.write(self.receipt_data)
            return True

    def get_items(self):
        if self.receipt_data:
            total_sum = 0
            soup = BeautifulSoup(self.receipt_data, "lxml")
            # rows = soup.findAll("div", { "class": "row"} )
            # items = rows.findAll("div", { "class": "col-xs-12"})[1:-1]
            rows = soup.select("div.row")
            # items_count = len(items)
            # print("Found items: {}".format(items_count))
            self.calculated_sum = 0

            def extract_text(row_obj):
                return row_obj.find('div', {'class': 'col-xs-4'}).get_text().encode("utf-8")

            items = []
            for i, row in enumerate(rows):
                if row.get_text().encode("utf-8") != "наименование товара (реквизиты)":
                    continue
                name = extract_text(rows[i + 1])
                price = float(extract_text(rows[i + 2]))
                count = int(float(extract_text(rows[i + 3])))
                summa = float(extract_text(rows[i + 4]))
                self.calculated_sum += summa
                if count != 1:
                    items.append(
                        ("{} ({} * {})".format(name, price, count),
                         "-{0:.1f}".format(summa)))
                else:
                    items.append((name, "-{0:.1f}".format(summa)))

            print("Items total sum: {}".format(self.calculated_sum))
            if self.calculated_sum != self.raw_sum:
                print(
                    "WARNING! Manually calculated sum is not equal to the receipt sum!")

            self.items = items
            return items
        else:
            print("No receipt data!")
            return False


class OFD1(OFDProvider):
    url_first_get = "https://consumer.1-ofd.ru/#/landing"
    url_receipt_get = "https://consumer.1-ofd.ru/api/tickets/ticket/{}"
    url_receipt_find = "https://consumer.1-ofd.ru/api/tickets/find-ticket"

    def is_suitable(self, data):
        return data['fiscal_drive_id'] and data['fiscal_id'] and data['fiscal_document_number']

    def search(self):
        print("Search in ofd1...")

        ofd1_payload = {
            "fiscalDocumentNumber":	self.fiscal_document_number,
            "fiscalDriveId":		self.fiscal_drive_id,
            "fiscalId":				self.fiscal_id
        }
        # fix for single quotes server error
        ofd1_payload = json.dumps(ofd1_payload, sort_keys=True)
        print(ofd1_payload)

        session = requests.Session()
        session.get(self.url_first_get)

        session.headers.update({
            'Content-Type': 'application/json',  # fix 415 error
            'X-XSRF-TOKEN': session.cookies.get_dict()['XSRF-TOKEN'],
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        })

        # print(session.headers)
        # print(session.cookies.get_dict())
        # cookies = session.cookies.get_dict().copy()
        # cookies.update({
        # 	'PLAY_LANG': 'ru'
        # })
        # print(cookies)

        ofd1 = session.post(self.url_receipt_find, data=ofd1_payload)

        print(ofd1.content)

        if (ofd1.status_code == 200):
            answer = ofd1.json()
            status = answer["status"]
            self.receipt_id = answer["uid"]

            print("Getting the receipt...")
            ofd1 = requests.get(self.url_receipt_get.format(self.receipt_id))

            if (ofd1.status_code == 200):
                self.raw = json.dumps(
                    ofd1.json(), ensure_ascii=False).encode('utf8')
                self.receipt_data = json.loads(self.raw)

                filename = self.get_receipt_file_name()

                if not os.path.exists(filename):
                    with open(filename, 'w') as outfile:
                        outfile.write(self.raw)
                else:
                    print("Ticket already saved!")
                    if not self.resend:
                        print("Skipping...")
                        return False
                return True
            else:
                print("Error {} while getting receipt from ofd1!".format(
                    ofd1.status_code))
                if config.debug:
                    print(ofd1.text)

        elif (ofd1.status_code == 404):
            print("Not found!")

        else:
            print("Error {} while searching in ofd1!".format(ofd1.status_code))
            if config.debug:
                print(ofd1.text)

        return False

    def get_items(self):
        if self.receipt_data:
            total_sum = 0
            items_count = len(self.receipt_data["ticket"]["items"])
            print("Found items: {}".format(items_count))

            items = []
            for item in self.receipt_data["ticket"]["items"]:
                data = item["commodity"]
                name = data["name"].encode('utf8')
                summa = data["sum"]
                price = data["price"]
                count = data["quantity"]
                total_sum += float(summa)

                if count != 1:
                    items.append(
                        ("{} ({} * {})".format(name, price, count),
                         "-{0:.1f}".format(summa)))
                else:
                    items.append((name, "-{0:.1f}".format(summa)))

            print("Items total sum: {}".format(total_sum))
            self.calculated_sum = str(total_sum)
            if self.calculated_sum != self.raw_sum:
                print(
                    "WARNING! Manually calculated sum is not equal to the receipt sum!")

            self.items = items
            return items
        else:
            print("No receipt data!")
            return False