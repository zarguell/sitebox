from sitebox.app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("sitebox.app:app", host="0.0.0.0", port=8000)
