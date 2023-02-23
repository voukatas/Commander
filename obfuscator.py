from Crypto.Cipher import AES
import base64


with open("Agents/agent.py", "r") as file:
    original_code = file.read()


key = b"my_secret_key_12"

# print(f"orig: {original_code}")

# Pad the original code to a multiple of 16 bytes to match the AES block size
padded_code = original_code.ljust(16 * ((len(original_code) + 15) // 16))

cipher = AES.new(key, AES.MODE_ECB)

# Encrypt the padded code using AES in ECB mode
encrypted_code = cipher.encrypt(padded_code.encode())

# Encode the encrypted code in Base64
encoded_code = base64.b64encode(encrypted_code)

# print("Obfuscated code: \n\n")
# print(encoded_code)

with open("Agents/obs_agent.py", "w") as f:
    f.write("import base64\n")
    f.write('from Crypto.Cipher import AES\n')
    f.write(f'encoded_code = {encoded_code}\n')
    f.write('key = b"my_secret_key_12"\n')
    f.write('cipher = AES.new(key, AES.MODE_ECB)\n')
    f.write('decoded_code = base64.b64decode(encoded_code)\n')
    f.write('decrypted_code = cipher.decrypt(decoded_code)\n')
    f.write('exec(decrypted_code.decode().rstrip())\n')

# Decode the Base64-encoded encrypted code
#decoded_code = base64.b64decode(encoded_code)

#decrypted_code = cipher.decrypt(decoded_code)

# print(decrypted_code.decode().rstrip())

# exec(decrypted_code.decode().rstrip())