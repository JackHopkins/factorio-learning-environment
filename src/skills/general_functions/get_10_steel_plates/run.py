from factorio_instance import FactorioInstance

factorio = FactorioInstance(address='localhost',
                                    bounding_box=200,
                                    tcp_port=27015,
                                    cache_scripts=False,
                                    inventory={
                                })

# Execute a snippet file
try:
    # Execute a snippet file
    factorio.run_snippet_file_in_factorio_env('snippet.py')
finally:
    # Ensure cleanup is called even if an exception occurs
    factorio.cleanup()