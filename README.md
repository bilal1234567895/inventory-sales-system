
# Inventory & Sales Management System

A Full Stack Python web application built using Django and SQLite to manage products, sales, suppliers, purchases, and inventory stock.

## Features

- User login and logout
- Add, edit, and delete products
- Search and filter products
- Record sales and automatically update stock
- Manage suppliers
- Restock products
- Record purchases
- View sales and purchase reports
- Filter reports by date
- Export sales and purchase reports to CSV
- Low-stock and out-of-stock alerts
- Dashboard with inventory and sales summaries

## Technologies Used

- Python
- Django
- SQLite
- HTML and CSS
- Git and GitHub

## How to Run

1. Open a terminal in the project folder.
2. Create and activate a Python virtual environment.
3. Install Django:

   `pip install "Django==4.2.30"`

4. Apply database migrations:

   `python manage.py migrate`

5. Create an administrator account:

   `python manage.py createsuperuser`

6. Start the development server:

   `python manage.py runserver`

7. Open http://127.0.0.1:8000/ in your browser.

## Database

This project uses SQLite. The local database file is excluded from GitHub. Database tables are created using Django migrations.

## Purpose

This project demonstrates Python web development, database management, CRUD operations, authentication, inventory tracking, and sales reporting.
