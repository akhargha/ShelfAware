import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
import matplotlib.pyplot as plt
from tensorflow.keras.applications import imagenet_utils
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# 1. Load Fine-Tuned Model
fine_tuned_model_path = '/Users/lucashyun/Trinity/weshack/model/fine_tuned_model.h5'  # Path to the Fine-Tuned model
fine_tuned_model = tf.keras.models.load_model(fine_tuned_model_path)

# Labels for the Fine-Tuned model
fine_tuned_labels = ['beverage', 'juice']  # Class names used during Fine-Tuning

# 2. Initialize MobileNetV2 (ImageNet Pretrained Model)
imagenet_model = tf.keras.applications.MobileNetV2(weights='imagenet')

# 3. Load and Display Image
filename = '/Users/lucashyun/Trinity/weshack/detected_objects/cluster_0.png'  # Path to the test image
img = image.load_img(filename, target_size=(224, 224))  # Resize the image to 224x224
plt.imshow(img)
plt.axis('off')
plt.show()

# 4. Preprocess the Image
resizedimg = image.img_to_array(img)  # Convert the image to a NumPy array
finalimg = np.expand_dims(resizedimg, axis=0)  # Expand dimensions to match input shape
finalimg = tf.keras.applications.mobilenet_v2.preprocess_input(finalimg)  # Preprocess for ImageNet model

# 5. Make Predictions with MobileNetV2 (ImageNet)
imagenet_predictions = imagenet_model.predict(finalimg)
imagenet_results = imagenet_utils.decode_predictions(imagenet_predictions, top=3)

# 6. Make Predictions with Fine-Tuned Model
fine_tuned_predictions = fine_tuned_model.predict(finalimg / 255.0)  # Fine-Tuned model expects [0, 1] normalized data
fine_tuned_index = np.argmax(fine_tuned_predictions)
fine_tuned_label = fine_tuned_labels[fine_tuned_index]
fine_tuned_confidence = fine_tuned_predictions[0][fine_tuned_index]

# 7. Output Results
print(f"Image File: {filename}")

# Print predictions from ImageNet model
print("\n[ImageNet (Pretrained MobileNetV2) Predictions]")
for i, (imagenet_id, label, confidence) in enumerate(imagenet_results[0]):
    print(f"{i + 1}. {label} (Confidence: {confidence:.2f})")

# Print predictions from Fine-Tuned model
print("\n[Fine-Tuned Model Prediction]")
print(f"Predicted Label: {fine_tuned_label} (Confidence: {fine_tuned_confidence:.2f})")

# Final decision: Compare Fine-Tuned model and ImageNet model predictions
print("\n[Final Decision]")
if fine_tuned_confidence > 0.5:  # Prioritize Fine-Tuned model if confidence is above 0.5
    print(f"Result: {fine_tuned_label} (from Fine-Tuned Model)")
else:
    print(f"Result: {imagenet_results[0][0][1]} (from ImageNet Model)")  # Use ImageNet prediction as fallback