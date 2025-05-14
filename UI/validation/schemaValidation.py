import json
from jsonschema import Draft202012Validator
import os

def load_schemas_from_path_by_type(path):
    """
    Loads all JSON schema files from the given directory path,
    using the 'const' value of the 'type' property as the key.

    Args:
        path (str): The path to the directory containing the schema files (.json).

    Returns:
        tuple: A tuple containing two dictionaries:
               - schemas_by_type: A dictionary where keys are the 'const' value of the
                                    'type' property from each schema and values are the
                                    loaded schema dictionaries.
               - validators_by_type: A dictionary where keys are the 'const' value of the
                                       'type' property from each schema and values are the
                                       corresponding JSON Schema validators.
    """
    schemas_by_type = {}
    validators_by_type = {}

    try:
        for filename in os.listdir(path):
            if filename.endswith(".schema.json") or filename.endswith(".json"):
                filepath = os.path.join(path, filename)
                try:
                    with open(filepath, "r") as f:
                        schema = json.load(f)
                        type_info = schema.get("properties", {}).get("type")
                        if type_info and type_info.get("const"):
                            message_type = type_info["const"]
                            schemas_by_type[message_type] = schema
                            validators_by_type[message_type] = Draft202012Validator(schema)
                        else:
                            print(f"Warning: Schema in '{filepath}' does not have a 'properties.type.const'. Filename: {filename}")
                except json.JSONDecodeError:
                    print(f"Error decoding JSON in '{filepath}'. Filename: {filename}")
                except FileNotFoundError:
                    print(f"Error: File not found at '{filepath}'.")
    except FileNotFoundError:
        print(f"Error: Directory not found at '{path}'.")
        return {}, {}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {}, {}

    return schemas_by_type, validators_by_type

if __name__ == '__main__':
    # Example usage (assuming you have a 'schemas' directory with your .schema.json files):
    schema_directory = "./schemas/responses/"  # Replace with the actual path to your schemas

    schemas, validators = load_schemas_from_path_by_type(schema_directory)
    print("Loaded Schemas (by type):")
    for msg_type, schema in schemas.items():
        print(f"- {msg_type}: {schema.get('title')}")

    print("\nLoaded Validators (by type):")
    for msg_type, validator in validators.items():
        print(f"- {msg_type}: {type(validator)}")