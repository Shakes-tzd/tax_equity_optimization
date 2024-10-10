# Solar System Allocation Project

This project is a Streamlit application for managing and optimizing solar system allocations across various funds based on complex constraints.

## Project Structure

```
solar_allocation_project/
│
├── main.py                  # Main entry point for the Streamlit app
├── config.py                # Configuration settings
├── constraints_models.py    # Pydantic models for constraints
├── optimization.py          # Optimization logic
│
├── utils/
│   ├── data_processing.py   # Data loading and saving functions
│   ├── constraint_processing.py # Constraint processing utilities
│   └── visualization.py     # Visualization functions
│
├── ui/
│   ├── constraint_editor.py  # UI for editing constraints
│   ├── optimization_runner.py # UI for running optimization
│   └── components.py         # Reusable UI components
│
├── data/
│   └── constraints/         # JSON files for constraints
│
└── requirements.txt         # Project dependencies
```

## Setup

1. Clone the repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Set up your database and update the connection string in `config.py`

## Running the Application

Run the Streamlit app with:

```
streamlit run main.py
```

## Usage

1. Use the Constraint Editor to modify fund constraints
2. Use the Optimization Runner to allocate systems to funds based on the defined constraints

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details