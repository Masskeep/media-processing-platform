self.onmessage = async (event) => {
    try {
        const hashBuffer = await crypto.subtle.digest("SHA-256", event.data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hash = hashArray
            .map((byte) => byte.toString(16).padStart(2, "0"))
            .join("");

        self.postMessage({ type: "success", hash });
    } catch (error) {
        self.postMessage({
            type: "error",
            message: error instanceof Error ? error.message : "Unable to hash file"
        });
    }
};
