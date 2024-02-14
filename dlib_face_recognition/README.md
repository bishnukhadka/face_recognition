Requirements for this dlib's face_recognition implimentation

1. Training_images folder
    - Inside this folder you will put your photo with it renamed with the persons name. eg. ram.jpeg

2. serviceAccount.json
    - This is to connect with your firebase account. 
   
        ```
        {
            "type": "service_account",
            "project_id": "collegemanagementappacem",
            "private_key_id": "<your-private-key-id>",
            "private_key": "<your-private-key>,
            "client_email": "<client-email>",
            "client_id": "<client_id>",
            "auth_uri": "<auth_uri>",
            "token_uri": "<token_uri>",
            "auth_provider_x509_cert_url": 'auth_provider_x509_cert_url",
            "client_x509_cert_url": "client_x509_cert_url",
            "universe_domain": "universe_domain"
        }

        ```

3. teachers.json
    - Key value pair of teachers' name(key) and ids(value)
    ```
        {
            "<name1>":"<id1>",
            "<name2>":"<id2>",
            "<name3>":"<id3>",
            "<name4>":"<id4>"
        }
    ```