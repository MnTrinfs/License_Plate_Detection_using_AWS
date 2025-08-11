<h1 align="center">
  <br>
  <a><img src="https://i.postimg.cc/BQj3wKwq/License-Plate-Logo-Black.png" alt="Logo" width="200"></a>
  <br>
  <h3 align="center">License_Plate_Detection_using_AWS</h3>
</h1>
<p align="center">My graduation project, making license plate detection website using AWS services</p>

[![Capture2.png](https://i.postimg.cc/BvQqqVn0/Capture2.png)](https://postimg.cc/JsvwxKX6)

## Demo
* Video: https://youtu.be/u93_ozLqg-s 
* Website: http://license-plate-bucket-mntri.s3-website-ap-southeast-2.amazonaws.com/

## Diagram
[![Diagram.png](https://i.postimg.cc/1t3ZQnM5/Diagram.png)](https://postimg.cc/67gPVQDD)
1. **User Upload** – The user uploads an image through the front-end interface. In the second diagram, this request passes through `Amazon CloudFront` (for content delivery) and `Amazon API Gateway` (to manage and route the API call).
2. **Store in S3** – The image is stored in an `Amazon S3 Bucket`.
3. **Trigger Lambda** – The upload event automatically triggers an `AWS Lambda` function.
4. **Call Rekognition** – The Lambda function sends an `IndexFaces` (or similar) request to `Amazon Rekognition`, providing the S3 object reference.
5. **Rekognition Fetches Image** – `Amazon Rekognition` retrieves the image from the S3 bucket for analysis.
6. **Return Results to Lambda** – Rekognition processes the image and returns metadata (e.g., detected faces, labels, confidence scores) to the Lambda function.
7. **Retrieve Object Metadata** – Lambda may also retrieve `HEAD Object` metadata from S3 (e.g., upload time, file size) to include in processing.
8. **Store in DynamoDB** – Lambda writes the processed results and relevant metadata into `Amazon DynamoDB` for indexing and future querying.
9. **Response to User** – (Second diagram) Processed data can be returned to the user via API Gateway and CloudFront.

