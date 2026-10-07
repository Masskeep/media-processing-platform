import { useEffect, useRef, useState } from "react";

function App() {
    const workerRef = useRef(null);

    const [selectedFile, setSelectedFile] = useState(null);
    const [hash, setHash] = useState("");

    const [error, setError] = useState("");

    useEffect(() => {
        const worker = new Worker(
            new URL("./workers/fileWorker.js", import.meta.url),
            {
                type: "module"
            }
        );

        workerRef.current = worker;

        worker.onmessage = (event) => {
            const data = event.data;

            if (data.type === "success") {
                setHash(data.hash);
                setError("");
            }

            if (data.type === "error") {
                setError(data.message);
                setHash("");
            }
        };

        return () => {
            worker.terminate();
        };
    }, []);

    const handleFileChange = async (event) => {
        const file = event.target.files[0];

        if (!file) {
            return;
        }

        setSelectedFile(file);
        setHash("");
        setError("");

        const allowedExtensions = ["mp4", "mov", "avi", "mkv"];

        const extension = file.name.split(".").pop().toLowerCase();

        if(!allowedExtensions.includes(extension)) {
          setError("Invalid file type. Please select a video file (mp4, mov, avi, mkv).");
          return;
        }

        const maxFileSize = 500 * 1024 * 1024; // 500 MB

        if(file.size > maxFileSize){
          setError("File size exceeds the maximum limit of 500 MB.");
          return;
        }

        setSelectedFile(file);

        

        const buffer = await file.arrayBuffer();

        workerRef.current.postMessage(buffer);
    };

    return (
        <div>
            <h1>File Hash Test</h1>

            <input
                type="file"
                onChange={handleFileChange}
            />

            {selectedFile && (
                <div>
                    <p>
                        File: {selectedFile.name}
                    </p>

                    <p>
                        Size: {selectedFile.size} bytes
                    </p>
                </div>
            )}

            {hash && (
                <div>
                    <p>SHA-256:</p>
                    <p>{hash}</p>
                </div>
            )}

            {error && (
                <p>
                    Error: {error}
                </p>
            )}
        </div>
    );
}

export default App;