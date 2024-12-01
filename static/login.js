document.addEventListener("DOMContentLoaded", function() {
  document.getElementById('signupForm').addEventListener('submit', function(event) {
    event.preventDefault();
    
    const formData = new FormData(this);
    fetch('/create-iam-user', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        const messageDiv = document.getElementById('signupMessage');
        if (data.error) {
            messageDiv.innerHTML = `<span style="color: red;">Error: ${data.error}</span>`;
        } else {
            messageDiv.innerHTML = `
                <span style="color: green;">Success! IAM User: ${data.user_name}</span><br>
                Access Key ID: ${data.access_key_id}<br>
                Secret Access Key: ${data.secret_access_key}<br>
                S3 Bucket: ${data.bucket_name}
            `;
        }
    })
    .catch(error => console.error('Error:', error));
  });
  
  document.getElementById('loginForm').addEventListener('submit', function(event) {
    event.preventDefault();
    
    const formData = new FormData(this);
    fetch('/login', {
      method: 'POST',
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      const messageDiv = document.getElementById('loginMessage');
      if (data.success) {
          messageDiv.innerHTML = `<span style="color: green;">Login successful! Redirecting...</span>`;
          setTimeout(() => {
              window.location.href = '/home'; // Redirect to home after successful login
          }, 2000);
      } else {
          messageDiv.innerHTML = `<span style="color: red;">Error: ${data.error}</span>`;
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('An error occurred: ' + error.message);
    });
  });


});