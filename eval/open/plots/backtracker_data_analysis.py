from env.src.instance import FactorioInstance
from env.src.models.game_state import GameState
from eval.open.db_client import PostgresDBClient
import os
def get_backtrackng_data(db, versions, model):
    
    version_mapping_data = {key : None for key in versions}
    for key, value in version_mapping_data.items():
        
        data = get_version_data(db, key)
        data = [x for x in data if x[0]["model"] == model and not x[0]["error_occurred"]]
        version_mapping_data[key] = data
    return version_mapping_data
def get_version_data(db, version):

    # Get most recent successful program to resume from
    query = f"""
    SELECT meta, code, response, achievements_json, state_json FROM programs 
    WHERE version = {version}
    ORDER BY created_at ASC
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
    return results


def initialise_game_states(data):
    instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                #cache_scripts=False,
                                )
    for version, version_data in data.items():
        for datapoint in version_data:
            game_state_obj = GameState.parse(datapoint[-1])
            instance.reset(game_state_obj)

if __name__ =="__main__":
    
    #create_a_simple_line_plot_complexities()
    #bar_chart()
    #create_a_simple_line_plot()
    db_client = PostgresDBClient(
        max_conversation_length=40,
        min_connections=2,
        max_connections=5,
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD")
    )
    versions = [2755, 2757]
    backtracking_data = get_backtrackng_data(db_client, versions, model = 'anthropic/claude-3.5-sonnet-open-router')
    initialise_game_states(backtracking_data)