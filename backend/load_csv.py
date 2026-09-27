import pandas as pd   # Import pandas so we can read CSV files

def load_csv(path: str) -> pd.DataFrame:
    """
    Loads a CSV file into a Pandas DataFrame.
    The 'path' argument must point to a real CSV file.
    """
    try:
        # Try to read the CSV file at the given path
        df = pd.read_csv(path)

        # If successful, print a confirmation message
        print("CSV loaded successfully.")

        # Return the DataFrame so the caller can use it
        return df

    except Exception as e:
        # If something goes wrong (bad path, missing file, etc.)
        print(f"Error loading CSV: {e}")
        return None

# This block only runs when THIS file is executed directly.
# It does NOT run when the file is imported by another module.
if __name__ == "__main__":

        # Print something so we know the script is actually running
        print("Script started")

        # Try to load the CSV file from the data folder
        df = load_csv("data/sample_data.csv")

        # If df is not None, print the first few rows
        if df is not None:
            print(df.head())
        else:
            print("No data to display.")
