import cv2
from ultralytics import YOLO
import easyocr
import os
import numpy as np
import json
import re
from collections import Counter

# 색상 매핑
HUMAN_COLOR = (0, 255, 0)  # 초록색: 인간
NON_HUMAN_COLOR = (255, 0, 0)  # 파란색: 인간이 아닌 객체

# EasyOCR 초기화
reader = easyocr.Reader(['en'])  # English 언어 모델 사용

# 배경 제거 후 저장
def remove_background_and_save(frame, mask, object_index, output_dir="detected_objects"):
    os.makedirs(output_dir, exist_ok=True)  # 출력 디렉토리 생성
    mask = mask.cpu().numpy().astype("uint8")  # 마스크 변환
    mask_resized = cv2.resize(mask, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)  # 마스크 크기 조정
    mask_resized = mask_resized * 255  # 마스크 값을 255로 확장 (0과 255)

    # 누끼 처리: 배경 제거
    foreground = cv2.bitwise_and(frame, frame, mask=mask_resized)

    # 객체 저장
    output_path = os.path.join(output_dir, f"object_{object_index}.png")
    cv2.imwrite(output_path, foreground)
    print(f"Saved non-human object: {output_path}")
    return output_path

# EasyOCR로 텍스트 추출
def extract_text_with_easyocr(image_path):
    results = reader.readtext(image_path)
    extracted_text = " ".join([res[1] for res in results])  # 추출된 텍스트 합치기
    print(f"Extracted text: {extracted_text}")
    return extracted_text

# YOLO 세그멘테이션 결과 시각화
def visualize_segmentation(frame, masks, labels, colors):
    for mask, label, color in zip(masks, labels, colors):
        mask = mask.cpu().numpy().astype("uint8")  # 마스크를 uint8로 변환
        mask_resized = cv2.resize(mask, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)  # 마스크 크기 조정
        overlay = np.zeros_like(frame, dtype=np.uint8)
        overlay[mask_resized == 1] = color  # 해당 객체 색상 적용
        frame = cv2.addWeighted(frame, 1, overlay, 0.5, 0)  # 오버레이 적용
        # 텍스트로 레이블 표시
        contours, _ = cv2.findContours(mask_resized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame

# 텍스트에서 반복되는 단어 추출 및 코퍼스 생성
def create_text_corpus(texts, min_frequency=2):
    # 모든 텍스트 데이터를 하나로 합치기
    all_text = " ".join(texts)
    
    # 소문자로 변환하고 특수 문자 제거
    all_text = re.sub(r'[^a-zA-Z\s]', '', all_text.lower())
    
    # 단어로 분할
    words = all_text.split()
    
    # 단어 빈도 계산
    word_counts = Counter(words)
    
    # 최소 빈도 이상 반복되는 단어만 코퍼스에 추가
    corpus = " ".join([word for word, count in word_counts.items() if count >= min_frequency])
    return corpus

# 텍스트 코퍼스 저장
def save_corpus_to_file(corpus, file_path="text_corpus.txt"):
    with open(file_path, "w") as file:
        file.write(corpus)
    print(f"Text corpus saved to {file_path}")

def main():
    # YOLO 모델 로드
    model = YOLO("yolov8n-seg.pt")  # YOLO 세그멘테이션 모델

    # YOLO 민감도 조정
    model.overrides["conf"] = 0.5  # Confidence threshold
    model.overrides["iou"] = 0.5   # IoU threshold

    # 웹캠 초기화
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Unable to access the webcam.")
        return

    print("Press 'q' to quit or wait for 10 non-human objects.")
    object_index = 0  # 객체 인덱스 초기화
    objects_data = []  # 객체 정보를 저장할 리스트
    non_human_count = 0  # 비인간 객체 수 카운트

    while non_human_count < 10:  # 비인간 객체가 10개 발견되면 종료
        ret, frame = cap.read()
        if not ret:
            break

        # YOLO 세그멘테이션 수행
        results = model(frame)

        masks, labels, colors = [], [], []
        non_human_objects = []  # non-human 객체의 마스크 저장
        for i, result in enumerate(results[0].boxes.data.tolist()):
            x1, y1, x2, y2, confidence, class_id = result
            label = model.names[int(class_id)]
            if label == "person":  # 인간 객체
                masks.append(results[0].masks.data[i])  # 마스크 추가
                labels.append("human")
                colors.append(HUMAN_COLOR)
            else:  # 인간이 아닌 객체
                mask = results[0].masks.data[i]
                masks.append(mask)  # 마스크 추가
                labels.append("non-human")
                colors.append(NON_HUMAN_COLOR)
                non_human_objects.append((mask, (x1, y1, x2, y2), confidence, label))  # non-human 객체 정보 저장

        # non-human 객체 처리
        for mask, (x1, y1, x2, y2), confidence, label in non_human_objects:
            if non_human_count >= 10:  # 10개 이상 비인간 객체를 추출하면 중단
                break

            object_path = remove_background_and_save(frame, mask, object_index)  # 누끼 따기 및 저장
            extracted_text = extract_text_with_easyocr(object_path)  # EasyOCR로 텍스트 추출

            # 객체 정보 JSON 저장 준비
            object_data = {
                "index": object_index,
                "bounding_box": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
                "confidence": round(confidence, 2),
                "label": label,
                "text": extracted_text,
                "image_path": object_path
            }
            objects_data.append(object_data)
            object_index += 1
            non_human_count += 1  # 비인간 객체 수 증가

        # 시각화
        segmented_frame = visualize_segmentation(frame, masks, labels, colors)

        # 비디오 디스플레이
        cv2.imshow("Human vs Non-Human Segmentation", segmented_frame)

        # 종료 조건 (수동 종료)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # JSON 파일로 객체 정보 저장
    with open("detected_objects.json", "w") as json_file:
        json.dump(objects_data, json_file, indent=4)
        print("Object data saved to detected_objects.json")

    cap.release()
    cv2.destroyAllWindows()

    # 텍스트 분석 및 코퍼스 생성
    non_human_texts = [obj["text"] for obj in objects_data if obj["label"] != "person"]
    corpus = create_text_corpus(non_human_texts)

    # 코퍼스 저장
    save_corpus_to_file(corpus)

if __name__ == "__main__":
    main()