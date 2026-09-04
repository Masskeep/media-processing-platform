import {useEffect, useState} from "react";



function App(){
 const [status, setStatus] = useState("");

 useEffect(() => {

        fetch("http://127.0.0.1:5000/health")

            .then(response => response.json())

            .then(data => {

                console.log(data);

                setStatus(data.status);

            });

    }, []);

 return(
  <div>
    <h1>Media Processing Plateform</h1>
    <p>Backend Status: {status}</p>
  </div>
 )
}

export default App;