import pandas as pd
import os

def homogenize_and_combine_csvs(file_paths, output_path, columns, default_values, remove_quotes=True):
    combined_df = pd.DataFrame(columns=columns)

    for file_path, defaults in zip(file_paths, default_values):
        # Load the CSV file with proper quote handling
        df = pd.read_csv(file_path, quotechar='"', skipinitialspace=True)

        # Print the DataFrame to verify content
        print(f"Data from {file_path}:")
        print(df.head())

        # Standardize column names
        df.columns = df.columns.str.strip().str.replace('SQL Query', 'Query')

        # Ensure the DataFrame has the required columns
        for col in columns:
            if col not in df.columns:
                df[col] = defaults.get(col, '')  # Add missing columns with default values

        # Set the Source column to "DIGITS" for prompt_sql.csv
        if 'prompt_sql.csv' in file_path:
            df['Source'] = 'DIGITS'

        # Select only the required columns
        df = df[columns]

        # Remove quotes from the specified columns
        if remove_quotes:
            for col in columns:
                df[col] = df[col].apply(lambda x: x.strip('"') if isinstance(x, str) else x)

        # Append to the combined DataFrame
        combined_df = pd.concat([combined_df, df], ignore_index=True)

    # Save the combined CSV
    combined_df.to_csv(output_path, index=False)

# Print the current working directory
print("Current working directory:", os.getcwd())

# Define the columns you want to standardize and their default values
standard_columns = ['Prompt', 'Query', 'Source']
default_values_ads = {'Source': 'ADS'}
default_values_prompt_sql = {'Source': 'DIGITS'}

# Use absolute paths for file paths
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
file_paths = [os.path.join(base_dir, 'data', 'ADSData_sql_prompts.csv'), os.path.join(base_dir, 'data', 'prompt_sql.csv')]
output_path = os.path.join(base_dir, 'data', 'combined_prompts_queries.csv')

# Create a combined CSV file
homogenize_and_combine_csvs(file_paths, output_path, standard_columns, [default_values_ads, default_values_prompt_sql])
