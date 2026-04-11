# Password Rotator for Windows and Linux by ki
#!/usr/bin/env python3

import secrets # unpredictable randomness
import string
import subprocess 
import platform

def generate_pass(length=16, specials = "!@#$%^&*"): # generate unique password
    chars = string.ascii_letters + string.digits + specials

    # check if password contains lowercase, uppercase, a digit and a special char
    max_attempts = 100
    attempts = 0

    while attempts < max_attempts: 
        attempts += 1
        password = ''.join(secrets.choice(chars) for _ in range(length))

        if (any(char.islower() for char in password) and
            any(char.isupper() for char in password) and
            any(char.isdigit() for char in password) and 
            any(char in specials for char in password)):
            print(f"Generated in {attempts} attempts")
            return password
        
    raise Exception("Failed to generate valid password")

def apply_password_linux(user, password):
    subprocess.run(
        ["chpasswd"], 
        input = f"{user}:{password}", 
        text = True,
        check = True
    )

def apply_password_win(user, password):
    subprocess.run(
        ["net", "user", user, password], 
        check = True
    )
    
def rotate_password(user):
    password = generate_pass() # generate pass
    print(f"{user} password updated: {password}") # prints for blue team records

    system = platform.system()

    # apply the password based on OS
    try: 
        if system == "Linux":
            apply_password_linux(user, password)
        elif system == "Windows":
            apply_password_win(user, password)
        else:
            raise Exception("Unsupported OS")
        return (user, password)
    
    except Exception as e: 
        print(f"Failed to rotate {user}'s password: {e}")
        return None
    
def get_regular_users(): # gets list of regular users based on OS
    system = platform.system()
    users = []

    if system == "Linux":
        try: # filter by UID
            uid_min = get_uid_min()

            result = subprocess.run( # coommand gets UIDs on system
                ['getent', 'passwd'],
                capture_output = True,
                text = True,
                check = True
            )

            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(':') # split by ':' found in format (ex. 'cooluser:x:1000:1000:...')
                    if len(parts) >= 3: # check if line actually contains creds
                        username = parts[0]
                        uid = int(parts[2])
                        if uid >= uid_min: # check if the uid is above the min
                            users.append(username)
            return users
        except Exception as e:
            print(f"Failed to get Linux users: {e}")
            return []
        
    elif system == "Windows": 
        try: # command gets local users on system
            ps_command = '''
            Get-LocalUser | 
            Where-Object { $_.Enabled -eq $true } | 
            Where-Object { $_.SID -like "S-1-5-21-*-*" } |
            Select-Object -ExpandProperty Name
            '''

            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                check=True
            )
            users = [u.strip() for u in result.stdout.strip().split('\n') if u.strip()]

            # filter out important accounts, so their account passwords don't change without direct specification
            exclude = ['administrator', 'guest', 'defaultaccount', 'admin']
            users = [u for u in users if u.lower() not in exclude]
            return users
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Failed to get Windows users: {e}")
            return []
    else:
        print(f"Unsupported OS: {system}")
        return []            
    
def get_uid_min(): # only works on Linux 
    system = platform.system()

    if system != "Linux": # Linux: reads from /etc/login.defs
        raise Exception(f"get_uid_min() is only for Linux systems. Current OS: {system}")
    
    try: # command to list UID_MIN
        result = subprocess.run(
            ['grep', '-E', '^UID_MIN', '/etc/login.defs'],
            capture_output = True,
            text = True,
            check = True
        )
        return int(result.stdout.split()[1])
    
    except subprocess.CalledProcessError:
        print("'UID_MIN' not found in /etc/login.defs")
        print("Please ensure the file contains a line like: UID_MIN 1000")
        raise 
    except FileNotFoundError:
        print("File /etc/login.defs not found")
        print("This system may not be a standard Linux distribution")
        raise
    except (ValueError, IndexError):
        print("Could not parse UID_MIN value from /etc/login.defs")
        raise
    
def rotate_localusers(): # rotate passwords for all reg users on system
    system = platform.system() 
    users = get_regular_users() 

    if not users:
        print("No regular users found to rotate passwords for")
        return []
    
    print(f"Found {len(users)} regular users: {', '. join(users)}")
    print(f"{'='*50}")

    # store results for each user
    results = []

    # loop through each user and rotate their password
    for user in users:
        print(f"\n--- Updating {user}'s Password ---")

        try:
            password = generate_pass()

            # Apply the password on OS
            if system == "Linux":
                apply_password_linux(user, password)
            elif system == "Windows":
                apply_password_win(user, password)
            else:
                raise Exception("Unsupported OS")
            
            # print for blue team records
            print(f"{user}'s password updated: {password}")
            results.append((user, password))
        except Exception as e:
            print(f"Failed to rotate {user}'s password: {e}")

    # Summary
    print(f"\n{'='*50}")
    print(f"Password rotation complete!")
    print(f"Successfully rotated: {len(results)/{len(users)}}")

    if results:
        print("\n Rotated Password List:")
        for user, password in results:
            print(f"{user}:{password}") 
    return results

def main():
    print("Password Rotation Tool")
    print("=" *40)
    print("1. Change password for a specific account")
    print("2. Change passwords for ALL local users")
    print("3. Exit")
    print("\n")

    try: 
        choice = input("Select option: 1, 2, or 3").strip()

        if choice == '1': # single user mode
            user = input("Enter account username: ")
            if not user:
                print("Rotating Password...")
                return
            print(f"\nRotating password for {user}...")
            result = rotate_password(user) # secure password generated inside 

            if result:
                print(f"\n Succesfully rotated password for {result[0]}")
                print(f"New password: {result[1]}")
            else:
                print(f"\n Failed to rotate password for {user}")
        elif choice == '2': # multiple users
            print("\nRotating passwords for ALL local users...")
            confirm = input(f"This will change passwords for ALL regular users. Continue? (yes/no): ").strip().lower()

            if confirm == 'yes' or confirm == 'y':
                results = rotate_localusers()    
                if not results:
                    print("\nNo passwords were rotated. Check system users.")
            else:
                print("Bye Bye!")
        elif choice == '3':
            print("Exiting...")
            return
        else:
            print("invalid option. Please select 1, 2, or 3.")

    except KeyboardInterrupt:
        print("\n Password Rotater cancceled by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
if __name__ == "__main__":
    main()