from fastapi import FastAPI
from pydantic import BaseModel
import json
from z3 import *
from fastapi.security import APIKeyHeader
from fastapi import HTTPException, Depends

app = FastAPI()

class TaskItem(BaseModel):
    tasks: list
    maxLoad: float
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tasks": [
                    [10, 0.1, 0.5, 0, 0, 0],
                    [13, 1, 0.5, 0.25, 1, 0.75],
                    [5, 0, 0.25, 0, 0.75, 0.1],
                    [3, 0, 0.1, 0, 0.1, 0],
                    [3, 0, 0.1, 0, 0.1, 0]
                    ],
                    "maxLoad": 1.1
                }
            ]
        }
    }
class InputData(BaseModel):
    data: TaskItem

#Il faudra mettre en place une recup des APIkey en BDD pour avoir la liste des valides. en attendant on va mettre une liste ne dur pour les test
api_key = APIKeyHeader(name="X-API-Key")

liste_api_key = ["poneychoucroute"]

async def get_api_key(api_key: str = Depends(api_key)):
    if api_key in liste_api_key:
        return api_key
    else:
        raise HTTPException(status_code=403, detail="Invalid API Key")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/optimize/")
def optimize_data(input_data: InputData, api_key: str = Depends(get_api_key)):
    data = input_data.data
    tasks = data.tasks
    maxLoad = data.maxLoad
    nbTasks = len(tasks)
    nbTeams = len(tasks[0]) - 1  # Subtract 1 for the value V

    # Declare the variables
    V = [Int('V{}'.format(i + 1)) for i in range(nbTasks)]
    C = [Bool('C{}'.format(i + 1)) for i in range(nbTasks)]
    Y = [[Real('Y{}_{}'.format(j + 1, i + 1)) for i in range(nbTasks)] for j in range(nbTeams)]
    # Create a Z3 solver instance
    solver = Optimize()

    # Add constraints for variable assignments
    for i in range(nbTasks):
        solver.add(V[i] == tasks[i][0])
        for j in range(nbTeams):
            solver.add(Y[j][i] == tasks[i][j + 1])  # Assign workload variables

    # Add constraints for workload totals
    for j in range(nbTeams):
        solver.add(Sum([If(C[i], Y[j][i], 0) for i in range(nbTasks)]) <= maxLoad)

    # Define the weighted sum for Vtot
    Vtot = Sum([If(C[i], V[i], 0) for i in range(nbTasks)])

    # Maximize Vtot
    solver.maximize(Vtot)

    if solver.check() == sat:
        model = solver.model()
        result = {
            "ValeurTotale": model.eval(Vtot).as_long()
        }

        for i in range(nbTasks):
            result["Tache{}".format(i + 1)] = bool(model.eval(C[i]))

        for j in range(nbTeams):
            result["ChargeEquipe{}".format(j + 1)] = model.eval(Sum([If(C[i], Y[j][i], 0) for i in range(nbTasks)])).as_decimal(10)

        return result
    else:
        return {"message": "No solution found."}
