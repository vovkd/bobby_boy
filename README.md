bobby_boy
===

### Предназначение

Распознавание QR-кодов с чеков и занесение трат в систему [Drebedengi.ru](http://drebedengi.ru).

Рабочий сценарий:
1. Запускаете программу
1. Подносите чек к веб-камере -> он распознаётся
1. Отправляются запросы в ОФД -> получаются данные чека и формируется список трат
1. Формируется табличный файл с данными по тратам
1. Открывается редактор таблиц -> проверяете и редактируете список
1. Закрываете редактор, нажимаете Enter -> список трат импортируется в Дребеденьги

При редактировании в файле также отображаются доступные категории трат, которые можно копировать в 
соответствующие позиций в чеке при необходимости. 

В настоящее время поддерживается работа с ОФД:
- [Первый ОФД](https://consumer.1-ofd.ru/#/landing) (Ашан, Виктория, Пятёрочка, BILLA, Магнит)
- [Платформа ОФД](https://lk.platformaofd.ru/web/noauth/cheque/search) (Дикси, Крошка-картошка)
- [Такском](https://receipt.taxcom.ru/) (Карусель, KFC)
- [OFD.RU](https://ofd.ru/checkinfo) (Связной) - потребуется ручной ввод РН ККТ и ИНН с чека
- [ОФД-Я](https://ofd-ya.ru/check) (Перекрёсток) - потребуется ручной ввод РН ККТ с чека (ИНН необязателен)
- ~~[Астрал ОФД](https://ofd.astralnalog.ru/)~~
- ~~[ОФД Яндекс](https://ofd.yandex.ru/)~~
- ~~[Контур ОФД](https://kontur.ru/ofd)~~

### Использование

Для выполнения программы достаточно запустить `main.py`. 

При первом запуске необходимо скопировать `config_template.py` в `config.py` и ввести свои данные:
- Логин и пароль от аккаунта в Дребеденьгах
- Валюту
- Место списания (счёт) 
- Категорию трат по умолчанию

Для ручного ввода уже распознанного с чека текста следует добавить ключ запуска `--text`.


### Установка

Необходим `Python 2.7`, фреймворки Pygame и ZBar и дополнительные библиотеки.

Работа проверена на Ubuntu Linux 16.04, для установки выполнить:
```
sudo apt-get build-dep python-pygame && sudo apt-get install python-dev
pip install -r requirements.txt
```

### Обсуждение

Отзывы и предложения по программе отправлять в соответствующую [ветку форума Drebedengi.ru](https://www.drebedengi.ru/?module=forumMessageList&topic_id=8486).