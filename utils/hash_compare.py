from PIL import Image
import imagehash


def print_image_hashes(image_path):
    img = Image.open(image_path).convert("RGB")
    print(f"▶ 파일: {image_path}")
    print(" - aHash :", imagehash.average_hash(img))
    print(" - pHash :", imagehash.phash(img))
    print(" - dHash :", imagehash.dhash(img))
    print(" - wHash :", imagehash.whash(img))
    print()


base_dir = r"C:\Users\osw\Desktop"
submit_path = base_dir + r"\버섯 원본_작은사이즈_제출.png"
answer_path = base_dir + r"\버섯 원본_작은사이즈_정답.png"

# 예시
print_image_hashes(submit_path)
print_image_hashes(answer_path)

hash1 = imagehash.phash(Image.open(submit_path))
hash2 = imagehash.phash(Image.open(submit_path))

diff = hash1 - hash2  # → 해밍 거리(Hamming distance)
print(f"차이: {diff} (0이면 완전 동일)")
