from PIL import Image
import os

def crop_images():
    img_path = '/home/ccs/.gemini/antigravity/brain/c18cfa8c-6785-4a84-a8fe-f8133a1ef713/uploaded_image_1763755970751.png'
    output_dir = 'blog/static/images/instagram_posts'
    os.makedirs(output_dir, exist_ok=True)

    img = Image.open(img_path)
    width, height = img.size
    
    # Assume 3 columns
    col_width = width // 3
    row_height = col_width # Square posts
    
    # We want 6 posts (2 rows)
    # Start from the bottom? Or assume header is at top.
    # Let's assume the grid starts after the header.
    # If height is 787 and 2 rows are ~682, header is ~105.
    # Let's try to find the start_y
    
    start_y = height - (row_height * 2)
    if start_y < 0: start_y = 0 # Fallback

    posts = []
    for row in range(2):
        for col in range(3):
            x1 = col * col_width
            y1 = start_y + (row * row_height)
            x2 = x1 + col_width
            y2 = y1 + row_height
            
            # Adjust for last column rounding
            if col == 2: x2 = width
            
            crop = img.crop((x1, y1, x2, y2))
            posts.append(crop)

    for i, post in enumerate(posts):
        if post.mode == 'RGBA':
            post = post.convert('RGB')
        post.save(f"{output_dir}/post_{i+1}.jpg")
        print(f"Saved post_{i+1}.jpg")

if __name__ == "__main__":
    crop_images()
