from fastapi import APIRouter, Depends

from api.common.services.rag import RAGClient
from api.dependencies import get_rag_client
from api.optimization.models.optimize import OptimizeQueryRequest
from api.structure.helpers.mongoToString import convert_db_structure_to_string
from api.structure.services.mongodb.getTables import get_db_structure


router = APIRouter(prefix="/optimize", tags=["optimization"])


@router.post("/")
def optimize_query(
    data: OptimizeQueryRequest, rag_client: RAGClient = Depends(get_rag_client)
):
    database_structure = get_db_structure("65ff3a7b8f1e4b23d4a9c1d2")
    string_structure = convert_db_structure_to_string(database_structure)

    # ask to rag to generate the optimization
    # response = rag_client.post("/rag/query/optimize", payload)

    # ask to rag to generate the command
    # response = rag_client.post("/rag/query/optimize", payload)

    # ask to rag to generate the command to create the db
    # response = rag_client.post("/rag/query/optimize", payload)

    # create the db instance

    # test the dbs

    # delete the db instance

    return None
