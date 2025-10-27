# Stage 2: Country Currency & Exchange API

This project is a RESTful API built with Python and Flask for the Backend Wizards Stage 2 task. The service fetches country and currency exchange data from two external APIs, processes and combines the data, and caches the results in a persistent MySQL database. It provides full CRUD (Create, Read, Delete) functionality for the cached data and can generate a dynamic summary image.

## Features

-   Fetches data from `restcountries.com` and `open.er-api.com`.
-   Calculates an estimated GDP for each country.
-   Caches all processed data in a MySQL database to ensure persistence.
-   Implements an "upsert" logic (UPDATE if exists, INSERT if not) for data refreshes.
-   Provides endpoints to get all countries, with support for filtering and sorting.
-   Provides endpoints to get and delete a specific country by name.
-   Generates a dynamic summary image (`.png`) with key statistics.
-   Handles external API failures and database connection errors gracefully.

## Technology Stack

-   **Language:** Python
-   **Framework:** Flask
-   **Database:** MySQL
-   **Production Server:** Gunicorn
-   **Libraries:**
    -   `requests`: For making HTTP requests to external APIs.
    -   `mysql-connector-python`: For connecting to the MySQL database.
    -   `python-dotenv`: For managing environment variables.
    -   `Pillow`: For generating the summary image.
-   **Hosting:** Railway

## API Endpoints

### 1. Refresh Country Data Cache
Fetches fresh data from external APIs, processes it, and updates the local MySQL database. Also regenerates the summary image.

-   **Endpoint:** `POST /countries/refresh`
-   **Success Response (`200 OK`):**
    ```json
    {
      "message": "Country data refreshed and cached successfully"
    }
    ```
-   **Error Response (`503 Service Unavailable`):** If an external API fails.

### 2. Get All Countries
Retrieves a list of all countries from the database cache. Supports filtering and sorting.

-   **Endpoint:** `GET /countries`
-   **Query Parameters (optional):**
    -   `region`: Filter by a specific region (e.g., `?region=Africa`).
    -   `currency`: Filter by a specific currency code (e.g., `?currency=USD`).
    -   `sort`: Sort results by GDP (e.g., `?sort=gdp_desc`).
-   **Success Response (`200 OK`):** An array of country objects.

### 3. Get a Specific Country
Retrieves a single country from the database by its name.

-   **Endpoint:** `GET /countries/<name>`
-   **Success Response (`200 OK`):** The JSON object for the requested country.
-   **Error Response (`404 Not Found`):** If the country does not exist in the database.

### 4. Delete a Country
Removes a country record from the database.

-   **Endpoint:** `DELETE /countries/<name>`
-   **Success Response (`204 No Content`):** Returns an empty body.
-   **Error Response (`404 Not Found`):** If the country does not exist.

### 5. Get API Status
Provides metadata about the current state of the database cache.

-   **Endpoint:** `GET /status`
-   **Success Response (`200 OK`):**
    ```json
    {
      "total_countries": 250,
      "last_refreshed_at": "2025-10-26T14:39:39Z"
    }
    ```

### 6. Get Summary Image
Serves the dynamically generated summary image.

-   **Endpoint:** `GET /countries/image`
-   **Success Response (`200 OK`):** The response body will be the `summary.png` image file.
-   **Error Response (`404 Not Found`):** If the image has not been generated yet.

## Setup and Local Installation

To run this project on your local machine, follow these steps:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/holmes1560/HNG13_Stage-2.git
    cd HNG13_Stage-2
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Environment Variables:**
    Create a file named `.env` in the root of the project. Copy the contents of `.env.example` (if provided) or use the structure below. Fill it with your MySQL database credentials.
    ```env
    # .env file
    DB_HOST=your_database_host
    DB_USER=your_database_username
    DB_PASSWORD=your_database_password
    DB_NAME=your_database_name
    ```

## Running the Application

Once the setup is complete, you can run the application:

```bash
python app.py
```

The application will start, initialize the database tables, and be accessible at `http://127.0.0.1:5000`.