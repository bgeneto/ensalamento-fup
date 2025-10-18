# Tech Stack: Sistema de Ensalamento FUP/UnB

This document outlines the core technologies chosen for the project, prioritizing rapid development and ease of self-hosting.

## Core Stack

* **Language:** **Python**
    * The entire application logic, backend, and frontend will be built using Python.
    * Use SOTA software design patterns like: DRY, KISS, SOC…
* **Framework:** **Streamlit**
    * Chosen for its ultra-fast development cycle for data-heavy, internal web applications. It serves as both the frontend (UI) and backend (server) logic. 
    * All CRUD operations must use `st.data_editor` with 'dynamic' `num_rows` for deletion  support, index column should be hidden for all tables using `hide_index=True` 
    * The Streamlit app will be a **multipage app** where some pages are public (for visualization, no auth) and most pages are protected via `streamlit-authenticator`. 
* **Authentication:** **streamlit-authenticator**
    * A community library for adding user login, logout, and password management directly within the Streamlit application.
    * Check `docs/streamlit-authenticator.md` for how to implement (documentation) streamlit-authenticator config file, register users, change password etc…
* **Data Models:** Use pydantic python module
* **User interface language:** no i18n, all the interface will be using **Brazilian Portuguese** as the only language!

## Database

* **Database:** **SQLite3**
    * Selected for its simplicity and zero-configuration "serverless" nature. The entire database is contained in a single file, which simplifies self-hosting and deployment, fitting the project's scale.
* **Data Access:** **SQLAlchemy**
    * Used as the ORM (Object Relational Mapper) or Core library to interact with the SQLite database. This provides a safe, robust, and Python-native way to handle all database queries.

## Deployment & Integrations

* **Deployment:** **Self-Hosted**
    * The application is intended to run on internal FUP/UnB servers.
* **Containerization (Recommended):** **Docker**
    * Using Docker is the recommended approach to package the Streamlit app, its Python dependencies, and the SQLite database file for consistent and reliable deployment.
    * Use both: Dockerfile and docker-compose.yaml
* **External API:** **Requests**
    * The `requests` library will be used to consume the external REST API from the "Sistema de Oferta" to import semester data.
* **Sending Emails**
    * Using Brevo (former Sendinblue) API with requests 
* **Parsing Schedules/Time slots**
    * Use the logic in file `docs/sigaa_parser.py`