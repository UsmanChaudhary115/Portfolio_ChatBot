from pyngrok import ngrok

# Expose your local port (e.g., 8000)
public_url = ngrok.connect(8000)
print("ngrok tunnel URL:", public_url)
