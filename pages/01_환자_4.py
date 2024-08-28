from Validation import validation_page

client_number = 5664

if __name__ == "__main__":
    validation_page(client_number, profile_version=5.1,
                    beh_dir_version=5.1, con_agent_version=5.1)
