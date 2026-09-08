import {useEffect, useState} from "react";



function App(){
 const [users, setUsers] = useState([]);
 const [error, setError] = useState("");
 const [name, setName] = useState("");
 const [email, setEmail] = useState("");

 const handleSubmit = (e)=> {
  e.preventDefault();
  fetch("/api/users", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    name: name,
    email: email
  })
})
  .then((response) => {
    return response.json().then((data) => {
      if (!response.ok) {
        throw new Error(data.error);
      }

      return data;
    });
  })
  .then((data) => {
    setError("");

    setUsers((currentUsers) => [...currentUsers, data]);

    setName("");
    setEmail("");
  })
  .catch((error) => {
    setError(error.message);
  });

 };

 useEffect(() => {
  fetch("/api/users")
  .then((response) => {
    if (!response.ok) {
      throw new Error(`Users request failed (${response.status})`);
    }
    return response.json();
  })
  .then((data) => {
    setUsers(data);
  })
  .catch((requestError) => {
    setError(requestError.message);
  })
 }, [])

 return(
  <div>
    <h1>Users</h1>
    <p>This is a list of all users in the system.</p>
    {error && <p>{error}</p>}

    <form onSubmit={handleSubmit}>
      <input
      type="text"
      value={name}
      onChange={(e) => setName(e.target.value)}
      placeholder="Name"
      />
      <input
      type="email"
      value={email}
      onChange={(e) => setEmail(e.target.value)}
      placeholder="Email"
      />
      <button type = "submit">Create User</button>
    </form>

    {users.map((user)=> {
      return(<div key = {user.id}>
        <h2>{user.name}</h2>
        <p>{user.email}</p>
      </div>)
    })}
  </div>
 ) 
}

export default App;