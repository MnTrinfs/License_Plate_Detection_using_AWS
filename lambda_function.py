import boto3
import base64
import uuid
import json
import logging
import re
from PIL import Image
import io
import base64
from boto3.dynamodb.conditions import Key

# Dictionary tra cứu mã vùng biển số
license_plate_regions = {
    "11": "Cao Bằng",
    "12": "Lạng Sơn",
    "14": "Quảng Ninh",
    "15": "Hải Phòng", "16": "Hải Phòng",
    "17": "Thái Bình → Hưng Yên",
    "18": "Nam Định → Ninh Bình",
    "19": "Phú Thọ",
    "20": "Thái Nguyên",
    "21": "Yên Bái → Lào Cai",
    "22": "Tuyên Quang",
    "23": "Hà Giang → Tuyên Quang",
    "24": "Lào Cai",
    "25": "Lai Châu",
    "26": "Sơn La",
    "27": "Điện Biên",
    "28": "Hòa Bình → Phú Thọ",
    "29": "Hà Nội", "30": "Hà Nội", "31": "Hà Nội", "32": "Hà Nội", "33": "Hà Nội", "40": "Hà Nội",
    "34": "Hải Dương → Hải Phòng",
    "35": "Ninh Bình",
    "36": "Thanh Hóa",
    "37": "Nghệ An",
    "38": "Hà Tĩnh",
    "39": "Đồng Nai",
    "41": "TP. Hồ Chí Minh",
    "43": "Đà Nẵng",
    "47": "Đắk Lắk",
    "48": "Đắk Nông → Lâm Đồng",
    "49": "Lâm Đồng",
    "50": "TP. Hồ Chí Minh", "51": "TP. Hồ Chí Minh", "52": "TP. Hồ Chí Minh", "53": "TP. Hồ Chí Minh",
    "54": "TP. Hồ Chí Minh", "55": "TP. Hồ Chí Minh", "56": "TP. Hồ Chí Minh", "57": "TP. Hồ Chí Minh",
    "58": "TP. Hồ Chí Minh", "59": "TP. Hồ Chí Minh",
    "60": "Đồng Nai",
    "61": "Bình Dương → TP. Hồ Chí Minh",
    "62": "Long An → Tây Ninh",
    "63": "Tiền Giang → Đồng Tháp",
    "64": "Vĩnh Long",
    "65": "Cần Thơ",
    "66": "Đồng Tháp",
    "67": "An Giang",
    "68": "Kiên Giang → An Giang",
    "69": "Cà Mau",
    "70": "Tây Ninh",
    "71": "Bến Tre → Vĩnh Long",
    "72": "BR-VT → TP. Hồ Chí Minh",
    "73": "Quảng Bình → Quảng Trị",
    "74": "Quảng Trị",
    "75": "Thừa Thiên Huế",
    "76": "Quảng Ngãi",
    "77": "Bình Định → Gia Lai",
    "78": "Phú Yên → Đắk Lắk",
    "79": "Khánh Hòa",
    "80": "Cục Cảnh sát giao thông",
    "T80": "Biển tạm thời",
    "81": "Gia Lai",
    "82": "Kon Tum → Quảng Ngãi",
    "83": "Sóc Trăng",
    "84": "Trà Vinh → Vĩnh Long",
    "85": "Ninh Thuận → Khánh Hòa",
    "86": "Bình Thuận → Lâm Đồng",
    "88": "Vĩnh Phúc → Phú Thọ",
    "89": "Hưng Yên",
    "90": "Hà Nam → Ninh Bình",
    "92": "Quảng Nam → Đà Nẵng",
    "93": "Bình Phước → Đồng Nai",
    "94": "Bạc Liêu → Cà Mau",
    "95": "Hậu Giang → Cần Thơ",
    "97": "Bắc Cạn → Thái Nguyên",
    "98": "Bắc Giang → Bắc Ninh",
    "99": "Bắc Ninh"
}

# Cấu hình logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Khởi tạo AWS clients
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')

# Định nghĩa tên S3 bucket và DynamoDB table
BUCKET_NAME = "license-plate-bucket-mntri"
TABLE_NAME = "LicensePlates"

def lambda_handler(event, context):
    try:
        logger.info("Received event: %s", json.dumps(event))

        # Xử lý request OPTIONS (CORS Preflight)
        if event.get("httpMethod") == "OPTIONS":
            return create_cors_response()

        # Kiểm tra dữ liệu đầu vào
        body = event.get('body', None)
        if not body:
            return create_response(400, {"error": "No data received"})

        body = json.loads(body)
        image_data = body.get("image_data", None)
        image_url = body.get("image_url", None)

        if not image_data and not image_url:
            return create_response(400, {"error": "No image data provided"})

        # Xử lý khi ảnh được gửi dưới dạng base64
        if image_data:
            try:
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                image_bytes = base64.b64decode(image_data)
                # Nhận diện màu biển số từ ảnh đã decode
                plate_color = detect_plate_color(image_bytes)
            except Exception as e:
                logger.error("Base64 decoding error: %s", str(e))
                return create_response(400, {"error": "Invalid base64 data"})

            file_name = f"uploads/{str(uuid.uuid4())}.jpg"
            s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=image_bytes, ContentType='image/jpeg')

        elif image_url:
            file_name = image_url.split("/")[-1]
            try:
                # Tải ảnh từ S3 để nhận diện màu
                response = s3.get_object(Bucket=BUCKET_NAME, Key=file_name)
                image_bytes = response['Body'].read()
                plate_color = detect_plate_color(image_bytes)
            except Exception as e:
                logger.error("Failed to get image from S3 for color detection: %s", str(e))
                plate_color = "Không xác định"

        # Gửi ảnh đến AWS Rekognition
        try:
            response = rekognition.detect_text(
                Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': file_name}}
            )
        except Exception as e:
            logger.error("Rekognition error: %s", str(e))
            return create_response(500, {"error": "Failed to process image with Rekognition"})

        # Trích xuất dữ liệu nhận dạng
        text_detections = response.get('TextDetections', [])

        # Lấy danh sách các từ đã nhận diện (WORD)
        detected_words = []
        for text_detection in text_detections:
            if text_detection['Type'] == 'WORD':
                detected_words.append(text_detection['DetectedText'])

        # Trích xuất biển số từ loại LINE có độ tin cậy cao
        license_plate, highest_confidence = extract_license_plate(text_detections)

        if not license_plate:
            return create_response(400, {"error": "No valid license plate detected"})

        # Lưu vào DynamoDB
        try:
            table = dynamodb.Table(TABLE_NAME)
            cloudfront_url = f"https://d2kvl2qxbf28mk.cloudfront.net/{file_name}"
            province = get_province_from_plate(license_plate)  
            item = {
                'ImageID': str(uuid.uuid4()),
                'PlateNumber': license_plate,
                'Province': province,
                'PlateColor': plate_color,
                'ImageURL': cloudfront_url
            }
            table.put_item(Item=item)
        except Exception as e:
            logger.error("DynamoDB error: %s", str(e))
            return create_response(500, {"error": "Failed to save to database"})

        # Truy vấn các biển số trùng khớp trong DynamoDB
        try:
            response = table.query(
                IndexName='PlateNumber-ImageID-index',
                KeyConditionExpression=Key('PlateNumber').eq(license_plate)
            )
            queried_items = response['Items']
            logger.info("Query result: %s", json.dumps(queried_items))
        except Exception as e:
            logger.error("Query DynamoDB error: %s", str(e))
            return create_response(500, {"error": "Failed to query database"})

        # Trả về cho frontend: plate + danh sách từ + ảnh + kết quả query
        return create_response(200, {
            "licensePlate": license_plate,
            "confidence": round(highest_confidence, 2),
            "detectedWords": detected_words,
            "imageURL": item['ImageURL'],
            "queriedItems": queried_items,
            "province": get_province_from_plate(license_plate),
            "plateColor": plate_color
        })

    except Exception as e:
        logger.error("Unhandled exception: %s", str(e), exc_info=True)
        return create_response(500, {"error": "Internal Server Error"})


def create_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        'body': json.dumps(body)
    }


def create_cors_response():
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "86400"
        },
        "body": json.dumps("Preflight request successful")
    }


def extract_license_plate(text_detections):
    # Ưu tiên LINE trước
    best_line = ""
    best_confidence = 0

    for detection in text_detections:
        if detection['Type'] == "LINE" and detection['Confidence'] > 70:
            text = detection['DetectedText'].replace(" ", "")
            if re.match(r"^[A-Z0-9.-]+$", text):
                if re.match(r"\d{2}[A-Z]-?[A-Z0-9]{2,5}(\.\d{2})?", text) and detection['Confidence'] > best_confidence:
                    best_line = text
                    best_confidence = detection['Confidence']

    if best_line:
        return best_line, best_confidence

    # Nếu không có LINE hợp lệ → fallback sang ghép từ WORD
    words = []
    for detection in text_detections:
        if detection['Type'] == "WORD" and detection['Confidence'] > 70:
            text = detection['DetectedText']
            if re.match(r"^[A-Z0-9.-]+$", text):
                words.append(text)

    candidate = "".join(words)
    candidate = re.sub(r"[^\w.-]", "", candidate)

    match = re.search(r"\d{2}[A-Z]-?[A-Z0-9]{2,5}(\.\d{2})?", candidate)
    if match:
        return match.group(0), 75  # Confidence thấp hơn LINE vì ghép tay
    elif candidate:
        return candidate, 60  # Có chuỗi ghép nhưng không khớp định dạng
    else:
        return "", 0




# def extract_license_plate(text_detections):
#     license_plate = ""
#     highest_confidence = 0
#     for detection in text_detections:
#         print("[INFO] detection: " + str(detection))
#         if detection['Type'] == "LINE" and detection['Confidence'] > 50:
#             detected_text = detection['DetectedText'].replace(" ", "")
#             if re.match(r"^[A-Z0-9-.]+$", detected_text) and detection['Confidence'] > highest_confidence:
#                 license_plate = detected_text
#                 highest_confidence = detection['Confidence']
#     return license_plate, highest_confidence

# def extract_license_plate(text_detections):
#     # Tìm tất cả từ loại WORD có chứa số hoặc chữ cái liên quan
#     words = []
#     for detection in text_detections:
#         if detection['Type'] == "WORD" and detection['Confidence'] > 70:
#             text = detection['DetectedText']
#             if re.match(r"^[A-Z0-9.-]+$", text):
#                 words.append(text)

#     # Ghép các từ lại thành 1 chuỗi biển số
#     candidate = "".join(words)

#     # Loại bỏ các dấu thừa nếu có, ví dụ 000.03. → 000.03
#     candidate = re.sub(r"[^\w.-]", "", candidate)

#     # Thử match theo định dạng chuẩn
#     match = re.search(r"\d{2}[A-Z]-?\d{3}\.?\d{2}", candidate)
#     if match:
#         return match.group(0), 100
#     else:
#         return candidate, 70



# Quét biển số xe máy
# def extract_license_plate(text_detections):
#     lines = []
#     for detection in text_detections:
#         if detection['Type'] == "LINE" and detection['Confidence'] > 70:
#             text = detection['DetectedText'].replace(" ", "")
#             if re.match(r"^[A-Z0-9.-]+$", text):
#                 lines.append(text)

#     # Nếu có ít nhất 2 dòng, ghép lại theo kiểu xe máy: dòng1 + dòng2
#     if len(lines) >= 2:
#         candidate = lines[0] + "-" + lines[1]
#     elif len(lines) == 1:
#         candidate = lines[0]
#     else:
#         return "", 0

#     # Chuẩn hóa biển số
#     candidate = re.sub(r"[^\w.-]", "", candidate)

#     # Ưu tiên khớp đúng định dạng xe máy hoặc xe hơi
#     match = re.search(r"\d{2}[A-Z]-?[A-Z0-9]{2,5}(\.\d{2})?", candidate)
#     if match:
#         return match.group(0), 100
#     else:
#         return candidate, 70


# Hàm tra cứu tỉnh từ biển số
def get_province_from_plate(plate_number):
    if not plate_number:
        return "Không xác định"
    plate_number = plate_number.replace(" ", "")  # Xử lý nếu có khoảng trắng
    prefix = plate_number.split('-')[0][:2]  # Lấy 2 chữ số đầu

    # Kiểm tra nếu mã vùng tồn tại trong dictionary
    province = license_plate_regions.get(prefix)
    if province:
        return province
    else:
        return "Không xác định"

def detect_plate_color(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        width, height = image.size

        # Cắt vùng trung tâm ảnh để tránh viền và chữ số
        cropped = image.crop((
            width * 0.2, height * 0.3,
            width * 0.8, height * 0.7
        ))

        # Resize nhỏ lại và lấy màu trung bình
        small = cropped.resize((1, 1))
        r, g, b = small.getpixel((0, 0))

        return classify_plate_color(r, g, b)
    except Exception as e:
        logger.error("Color detection failed: %s", str(e))
        return "Không xác định"

def classify_plate_color(r, g, b):
    if r > 200 and g > 200 and b > 200:
        return "Trắng"
    elif r > 200 and g > 200 and b < 100:
        return "Vàng"
    elif b > 180 and r < 100 and g < 100:
        return "Xanh"
    elif r > 150 and g < 50 and b < 50:
        return "Đỏ"
    else:
        return "Không xác định"
