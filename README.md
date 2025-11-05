# E-commerce Project


## Overview
This e-commerce project is designed to provide a robust platform for online shopping. It includes features for user registration, product management, cart functionality, order processing, and customer support. The application is built using Python and follows a modular architecture, separating domain logic, services, and application entry points.


## Features
- User registration and authentication
- Product catalog with active/inactive status
- Shopping cart management
- Order processing with payment integration
- Delivery tracking and management
- Customer support through message threads


## Project Structure
```
projet_ecommerce
├── src
│   ├── __init__.py
│   ├── domain.py        # Core domain models and business logic
│   ├── services.py      # Service classes for business logic
│   └── main.py          # Entry point for the application
├── tests
│   ├── test_domain.py   # Unit tests for domain models
│   └── test_order_flow.py # Tests for order processing flow
├── docs
│   ├── USER_STORIES.md   # User stories for the application
│   └── SPECIFICATIONS.md  # Detailed project specifications
├── pyproject.toml        # Project configuration
├── requirements.txt      # Required Python packages
├── .gitignore            # Files to ignore in version control
└── README.md             # Project documentation
```




2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```


3. Run the application:
   ```
   python run.py
   ```


## Usage
- Access the application through your web browser at `http://localhost:5000`.
- Follow the on-screen instructions to register, log in, and start shopping.


## Testing
To run the tests, use the following command:
```
pytest tests/
```



