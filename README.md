# bookstore
Проектирование и разработка приложения «Книжный интернет-магазин» с микросервисной архитектурой. Стек – Python (Flask) + PostgreSQL. Создание UML-диаграмм и схемы таблиц БД, разработка веб-приложения

Веб-приложение состоит из трех микросервисов: book_catalog_service, user_service и order_service.

Каждый микросервис имеет свою базу данных и работает на своем порту. Каждый микросервис работает независимо от остальных. Так, при работе только микросервиса с каталогом книг, у пользователя есть возможность поиска книги в каталоге и просмотра деталей о товаре, но нет возможности авторизации и просмотра своих заказов. Обмен данными между сервисами происходит с помощью REST API. Если сервису user_service нужно получить доступ к данным о книгам по их id, он отправляет запрос микросервису book_catalog_service, так как не имеет доступа к базе данных с книгами. Для запуска каждого микросервиса отдельно нужно в директории сервиса в терминале ввести "python app.py"
