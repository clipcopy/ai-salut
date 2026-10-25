import os

def filter_logins(keyword, filename):
    filtered_logins = []
    with open(filename, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            if keyword in line:
                filtered_logins.append(line.strip())
    return filtered_logins

def sanitize_keyword(keyword):
    """Sanitize keyword for safe filenames and folder names"""
    safe = keyword.replace(":", "_").replace("/", "_").replace("\\", "_")
    safe = safe.replace(".", "_")  # optional: replace dot for folder safety
    return safe

def ensure_folder(folder_name):
    """Create folder if it doesn't exist"""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name

def main():
    # kunin lahat ng .txt files maliban sa host_config.txt at output files
    list_files = [f for f in os.listdir('.') if f.endswith('.txt') and f != 'host_config.txt']

    # load keywords mula sa host_config.txt
    with open('host_config.txt', 'r', encoding='ISO-8859-1') as config_file:
        keywords = [k.strip() for k in config_file.read().splitlines() if k.strip()]

    # loop bawat list file
    for list_filename in list_files:
        print(f"\nProcessing list file: {list_filename}")
        for keyword in keywords:
            filtered_logins = filter_logins(keyword, list_filename)
            sanitized_keyword = sanitize_keyword(keyword)
            
            if filtered_logins:
                # make folder for keyword (e.g. google.com -> google)
                folder_name = sanitized_keyword.split("_")[0]  # get first part (e.g. google)
                folder_path = ensure_folder(folder_name)

                # build output file path inside folder
                output_filename = f"{list_filename}-{sanitized_keyword}-{len(filtered_logins)}.txt"
                output_path = os.path.join(folder_path, output_filename)

                # write results
                with open(output_path, "w", encoding="utf-8") as output_file:
                    output_file.write("\n".join(filtered_logins))

                print(f"Configs: '{keyword}' - Found {len(filtered_logins)} logins (saved to {output_path})")
            else:
                print(f"Configs: '{keyword}' - Found 0 logins")

if __name__ == "__main__":
    main()
