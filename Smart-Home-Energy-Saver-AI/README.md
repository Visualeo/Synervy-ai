# Smart-Home-Energy-Saver-AI

An intelligent, agent-based system for optimizing and predicting home energy usage, combining a Fast API backend with a Streamlit interface.

## Project Structure

```
Smart-Home-Energy-Saver-AI/
│
├── backend/
│   ├── api/
│   ├── agents/
│   ├── services/
│   └── main.py
│
├── frontend/
│   └── app.py (Streamlit App)
│
├── ml/
│   ├── models/
│   ├── training/
│   └── prediction.py
│
├── data/
├── artifacts/
├── static/
├── templates/
├── .env
├── requirements.txt
└── README.md
```

## Setup & Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   cd Smart-Home-Energy-Saver-AI
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Mac/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

You can start either the backend or the frontend via the following clean start commands.

To start the **FastAPI Backend Server**:
```bash
python backend/main.py
```

To start the **Streamlit Frontend**:
```bash
streamlit run frontend/app.py
```

## Features

- **Agent-Based Architecture**: Utilizes specialized AI agents for monitoring, prediction, decision-making, and execution.
- **Machine Learning**: Prophet models predict `kWh` consumption based on household size, weekend indicator, and temperature.
- **Microservice Design**: Modular backend services with decoupled UI elements.
