import { useEffect, useRef, useState } from "react";
import { apiRequest } from "./api";


function App() {
    const workerRef = useRef(null);

    const [selectedFile, setSelectedFile] = useState(null);
    const [hash, setHash] = useState("");
    

    const [error, setError] = useState("");

    const [user, setUser] = useState(null);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [isLoggedIn, setIsLoggedIn] = useState(false);

    const [isUploading, setIsUplaoding] = useState(false);
    const [uploadSession, setUploadSession] = useState(null);

    const [uploadedParts, setuploadedParts] = useState([]);

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


    useEffect(() =>{
        const token = sessionStorage.getItem("access_token");

        if(!token){
            return;
        }

        apiRequest("/api/auth/me").then((data) => {
            setUser(data);
        })
        .catch(() => {
            sessionStorage.removeItem("access_token");
            sessionStorage.removeItem("refresh_token");
        })
    }, []);

    const handleLogin = async (event) => {
         event.preventDefault();

         setError("");
         setIsLoggedIn(true);

         try{
            const data = await apiRequest("/api/auth/login", {
                   method: "POST",
                   headers:{
                    "Content-Type": "application/json"
                   },
                   body: JSON.stringify({
                    email,
                    password
                   })
            });

            sessionStorage.setItem("access_token", data.access_token);
            sessionStorage.setItem("refresh_token", data.refresh_token);
            
            setUser(data.user);
            setPassword("");
         }catch(err){
            setError(err.message);
         }
         finally{
            setIsLoggedIn(false);
         }
    };

    const handleStartUpload = async() =>{
        if(!selectedFile){
            setError("Please select a Video file before starting the upload.");
            return;
        }
       setError("");
       setUploadSession(null);
       setIsUplaoding(true);

       try{
        const data = await apiRequest("/api/media/multipart-upload/start", {
            method: "POST",
            headers:{
                "Content-Type": "application/json"
            },
            body : JSON.stringify({
                filename: selectedFile.name,
                content_type: selectedFile.type,
                file_size: selectedFile.size
            })
        });
        setUploadSession(data);
       }catch(err){
        setError(err.message);
       }finally{
        setIsUplaoding(false);
       }
    }

    const handleUploadParts = async() =>{

        if(!selectedFile || !uploadSession){
            setError("Please select a file and start the upload session before uploading parts.");
            return;
        }

        setError("");
        setIsUplaoding(true);

        try{
            const partSize = uploadSession.chunk_size;
            const parts = [];

            for(
                let partNumber = 1;
                partNumber <= uploadSession.total_chunks;
                partNumber++
            ){
                const start = (partNumber - 1) * partSize;
                const end = Math.min(start + partSize, selectedFile.size);
                
                const filePart = selectedFile.slice(start, end);

                const urlData = await apiRequest(
                    `/api/media/multipart-upload/${uploadSession.upload_id}/part/${partNumber}/url`,
                    {
                        method: "POST"
                    }
                );

                const s3Response = await fetch(urlData.presigned_url, {
                    method: "PUT",
                    body : filePart
                });

                if(!s3Response.ok){
                    throw new Error(`Failed to upload part ${partNumber}`);
                }

                const eTag= s3Response.headers.get("ETag");

                if(!eTag){

                    throw new Error(`ETag not found for part ${partNumber}`);
                }

                parts.push({
                    part_number: partNumber,
                    eTag: eTag
                });
            
            }


             setuploadedParts(parts);
        }

       catch(err){
        setError(err.message);
       }finally{
        setIsUplaoding(false);
       }

    }

    const handleCompleteUpload = async() => {
        if(!uploadSession || uploadedParts.length === 0){
            setError("Please upload parts before completing the upload.");
            return;
        }

        setError("");
        setIsUplaoding(true);

        try{
            const data = await apiRequest(
                `api/media/multipart-upload/${uploadSession.upload_id}/complete`,
                {
                    method: "POST",
                    headers:{
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        parts: uploadedParts
                    })
                }
            );

            console.log("Upload completed successfully:", data);

            setError("");
            alert("Upload completed successfully!");

        }catch(err){
            setError(err.message);
        }
        finally{
            setIsUplaoding(false);
        }
    }

    const handleLogout = () => {
        sessionStorage.removeItem("access_token");
        sessionStorage.removeItem("refresh_token");
        
        
        setUser(null);
        setSelectedFile(null);
        setHash("");
        setError("");
    };

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

   if(!user){
    return (
        <div>
            <h1>Media Processing Plateform</h1>
            <h2>Login</h2>

            <form onSubmit={handleLogin}>
            <div>
                <label htmlFor="email">Email:</label>
                <input
                    type="email"
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                />
            </div>
            <div>
                <label htmlFor="password">Password:</label>
                <input
                    type="password"
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                />
            </div>
            {error && <p style={{ color: "red" }}>{error}</p>}
            <div>
                <button type="submit" disabled={isLoggedIn}>
                    {isLoggedIn ? "Logging in..." : "Login"}
                </button>
            </div>
            
            </form>
            {error && <p style={{ color: "red" }}>{error}</p>}
        </div>
    );
   }

   return (
    <div>

        <h1>Media Processing Platform</h1>

        <p>Logged in as : {user.email}</p>

        <button onClick={handleLogout}>Logout</button>

        <hr />

        <h2>File Hash Test</h2>

        <input type = "file" 
        accept = ".mp4,.mov,.avi,.mkv"
        onChange={handleFileChange}
        />

           {hash && (
            <div>
                    <p>SHA-256 Hash: {hash}</p>
                    <p>{hash}</p>
                </div>
        )}

        <button
        onClick={handleStartUpload}
        disabled = {!selectedFile || isUploading}
        >{isUploading ? "Uploading..." : "Start Upload"}</button>

        {selectedFile && (
            <div>
                <p>Selected File: {selectedFile.name}</p>
                <p>Size : {selectedFile.size} bytes</p>
            </div>
        )}

        {
            uploadSession && (
                <div>
                    <h3>Upload Session</h3>
                    <p>Session ID: {uploadSession.upload_id}</p>
                    <p>Total Chunks: {uploadSession.total_chunks}</p>
                    <p>Chunk Size: {uploadSession.chunk_size} bytes</p>
                </div>
            )
        }
        <button onClick={handleUploadParts}
        disabled = {!uploadSession || isUploading || uploadedParts.length > 0}
        >{isUploading ? "Uploading..." : "Upload Parts"}</button>

        {
            uploadedParts.length > 0 && (
                <div>

                    <h3>Uploaded Parts</h3>
                    <p>Successfully uploaded {uploadedParts.length} parts.</p>
                    </div>
            )
        }

        <button
        
        onClick={handleCompleteUpload}
        disabled = {!uploadSession || uploadedParts.length === 0 || isUploading}>
        Complete Upload
        </button>

     

        {error && <p style={{ color: "red" }}>{error}</p>}
    </div>
   );
}

export default App;