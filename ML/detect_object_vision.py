# 필요한 라이브러리 임포트
import cv2
from ultralytics import YOLO
import easyocr
import os
import numpy as np
import json

# EasyOCR 초기화
reader = easyocr.Reader(['en'])  # English 언어 모델 사용

# YOLO 모델 로드 (경량 모델)
model = YOLO("yolov8n-seg.pt")

# YOLO 민감도 조정
model.overrides["conf"] = 0.4  # Confidence threshold
model.overrides["iou"] = 0.5   # IoU threshold

# 근거리 객체 기준
MIN_OBJECT_SIZE_RATIO = 0.2  # 프레임 높이의 20% 이상 크기인 객체만 근거리로 간주

# 객체 저장 및 OCR 적용
def save_object_and_extract_text(frame, mask, object_index, confidence_threshold=0.6, output_dir="detected_objects"):
    os.makedirs(output_dir, exist_ok=True)  # 출력 디렉토리 생성
    mask = mask.cpu().numpy().astype("uint8") * 255
    mask_resized = cv2.resize(mask, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)

    # 배경 제거
    foreground = cv2.bitwise_and(frame, frame, mask=mask_resized)

    # 객체 저장
    output_path = os.path.join(output_dir, f"object_{object_index}.png")
    cv2.imwrite(output_path, foreground)

    # EasyOCR로 텍스트 추출
    results = reader.readtext(output_path)
    filtered_texts = [res[1] for res in results if res[2] >= confidence_threshold]  # 신뢰도 조건 필터링
    extracted_text = " ".join(filtered_texts)  # 필터링된 텍스트 합치기

    return extracted_text, output_path

# 코퍼스 저장
def save_corpus_to_file(corpus, file_path="text_corpus.txt"):
    with open(file_path, "w") as file:
        file.write(corpus)
    print(f"Text corpus saved to {file_path}")

# YOLO 세그멘테이션 시각화
def visualize_segmentation(frame, masks, labels, colors):
    for mask, label, color in zip(masks, labels, colors):
        mask = mask.cpu().numpy().astype("uint8")
        mask_resized = cv2.resize(mask, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)

        # Bounding Box 및 텍스트 표시
        contours, _ = cv2.findContours(mask_resized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)  # Bounding Box
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame

# 메인 루프
def main():
    # 웹캠 초기화
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Unable to access the webcam.")
        return

    print("Video will stop automatically when 3-4 high-confidence texts are collected.")
    object_index = 0  # 객체 인덱스 초기화
    objects_data = []  # 객체 정보를 저장할 리스트
    corpus_texts = []  # 코퍼스에 포함될 텍스트 저장 리스트

    # 신뢰도 높은 텍스트 수집 기준
    REQUIRED_HIGH_CONFIDENCE_TEXTS = 3  # 최소 수집 텍스트 개수
    CONFIDENCE_THRESHOLD = 0.6  # OCR Confidence Rate 기준

    while len(corpus_texts) < REQUIRED_HIGH_CONFIDENCE_TEXTS:  # 텍스트가 충분히 수집될 때까지 반복
        ret, frame = cap.read()
        if not ret:
            break

        frame_height, frame_width, _ = frame.shape  # 프레임 크기
        min_object_size = frame_height * MIN_OBJECT_SIZE_RATIO  # 근거리 객체 크기 기준

        # YOLO 세그멘테이션 수행
        results = model(frame)

        masks, labels, colors = [], [], []
        for i, result in enumerate(results[0].boxes.data.tolist()):
            x1, y1, x2, y2, confidence, class_id = result
            label = model.names[int(class_id)]
            mask = results[0].masks.data[i]
            object_height = y2 - y1  # 객체 높이
            object_width = x2 - x1  # 객체 너비

            # 근거리 객체 필터링
            if object_height < min_object_size or object_width < min_object_size:
                continue  # 근거리 객체가 아니면 무시

            # 객체 저장 및 OCR
            extracted_text, object_path = save_object_and_extract_text(
                frame, mask, object_index, confidence_threshold=CONFIDENCE_THRESHOLD
            )

            # OCR 결과가 신뢰도 조건에 부합하는 경우 처리
            if extracted_text:
                objects_data.append({
                    "index": object_index,
                    "bounding_box": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
                    "confidence": round(confidence, 2),
                    "label": label,
                    "text": extracted_text,
                    "image_path": object_path
                })
                corpus_texts.append(extracted_text)
                object_index += 1

                print(f"Collected text: {extracted_text}")

        # 시각화
        segmented_frame = visualize_segmentation(frame, masks, labels, colors)

        # 비디오 디스플레이
        cv2.imshow("Confidence-Based Object Segmentation", segmented_frame)

        # 종료 조건 (수동 종료)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Manual termination.")
            break

    # JSON 파일로 객체 정보 저장
    with open("detected_objects.json", "w") as json_file:
        json.dump(objects_data, json_file, indent=4)
        print("Object data saved to detected_objects.json")

    # 코퍼스 생성 및 저장
    corpus = "\n".join(corpus_texts)  # 텍스트를 줄바꿈으로 구분
    save_corpus_to_file(corpus)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()