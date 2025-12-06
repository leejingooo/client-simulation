from Validation import validation_page

client_number = 6106

if __name__ == "__main__":
    validation_page(client_number, profile_version=6.0,
                    beh_dir_version=6.0, con_agent_version=6.0)
