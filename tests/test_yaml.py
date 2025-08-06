import yaml

def test_yaml_load(file_path):
    """
    Test loading a YAML file to ensure it's properly formatted.
    
    Args:
        file_path (str): Path to the YAML file to test
        
    Returns:
        bool: True if the file loaded successfully, False otherwise
    """
    try:
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
        print(f"YAML file {file_path} loaded successfully!")
        
        # Print the first agent's collaborations to verify format
        first_agent = next(iter(data))
        print(f"\nSample collaborations from {first_agent}:")
        collaborations = data[first_agent].get('collaborations', {})
        for agent, description in collaborations.items():
            print(f"  {agent}: {description}")
            
        return True
    except yaml.YAMLError as e:
        print(f"Error loading YAML file: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    # Test the updated agents.yaml file
    test_yaml_load("src/scribe/config/agents.yaml")