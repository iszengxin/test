from PIL import Image, ImageDraw, ImageFont
import cv2
import os
import json
from tqdm import tqdm
import random
import unicodedata
# from translate import translate_one
def merge_sentences(sentences, lines):
    # 计算每个句子的长度
    sentence_lengths = [len(sentence) for sentence in sentences]
    
    # 计算目标长度
    total_length = sum(sentence_lengths)
    target_length = total_length / lines
    
    # 初始化结果列表
    merged_sentences = []
    current_length = 0
    current_sentence = ""
    
    for sentence in sentences:
        # 如果当前句子加上当前长度超过目标长度，并且当前句子不为空，则合并并添加到结果列表
        if current_length + len(sentence) > target_length and current_sentence:
            merged_sentences.append(current_sentence)
            current_sentence = sentence
            current_length = len(sentence)
        else:
            # 否则，继续合并句子
            if current_sentence:
                current_sentence += " " + sentence
            else:
                current_sentence = sentence
            current_length += len(sentence) + 1  # 加上空格的长度
    
    # 添加最后一个合并的句子
    if current_sentence:
        merged_sentences.append(current_sentence)
    
    # 如果合并后的句子数量少于目标行数，直接返回
    if len(merged_sentences) <= lines:
        return merged_sentences
    
    # 如果合并后的句子数量多于目标行数，尝试进一步合并
    while len(merged_sentences) > lines:
        # 找到长度最短的两个相邻句子进行合并
        min_index = 0
        min_length = len(merged_sentences[0]) + len(merged_sentences[1])
        for i in range(1, len(merged_sentences) - 1):
            current_length = len(merged_sentences[i]) + len(merged_sentences[i + 1])
            if current_length < min_length:
                min_index = i
                min_length = current_length
        
        # 合并最短的两个相邻句子
        merged_sentences[min_index] = merged_sentences[min_index] + " " + merged_sentences[min_index + 1]
        del merged_sentences[min_index + 1]
    
    return merged_sentences

def draw_x1y1x2y2(location_list, image_path, save_path,final_and_box=False):
    # ########## draw ##########
    image = cv2.imread(image_path)
    for idx,location in enumerate(location_list):
        if final_and_box:
            color = (0, 255, 0) if idx == 0 else (255, 0, 255)
        else:
            color = (0, 255, 0)
        final_location = map(int,location)
        x, y, x2, y2 = final_location

        cv2.rectangle(image, (x, y), (x2, y2),color , 2)  # 绿色，线宽为2

    cv2.imwrite(save_path, image)

def check_ok(location,boxes):
    # x1_now, y1_now, x2_now, y2_now = location
    x1_b1, y1_b1, x2_b1, y2_b1 = location
    for box in boxes:
        #  x1, y1, x2, y2 = box
        x1_b2, y1_b2, x2_b2, y2_b2 = box
        x_overlap = not (x2_b1 <= x1_b2 or x2_b2 <= x1_b1)
        y_overlap = not (y2_b1 <= y1_b2 or y2_b2 <= y1_b1)

        if x_overlap and y_overlap:
            return False
        
        if x2_b2<=x1_b2:
            return False
        if y2_b2<=y1_b2:
            return False

    return True

def check_ok_one(box):
    x1,y1,x2,y2 = box
    if x2<x1:
        return False
    if y2<y1:
        return False
    
    return True

def get_area(location):
    x, y, x2, y2 = location
    w = x2-x
    h = y2-y
    return w*h

def find_max_rectangles(boxes,
                        image_weight,
                        image_height,
                        max_box_height,
                        location,
                        image_path,
                        detect_path=None):
    # final_location = None
    # final_max_area = 0
    # final_word_vertical = 'center'

    word_vertical_dict = {0: "top", 1: "bottom", 2: "center", 3: 'center'}

    all_box_info = []

    for box in boxes:
        x1_now, y1_now, x2_now, y2_now = box

        # 以检测框最下面那条边为top的最大矩形
        # x1_list = [x2 for x1, y1, x2, y2 in boxes if x1 < x2_now and y2>y2_now]
        x1_list = [x2 for x1, y1, x2, y2 in boxes if x1 < x2_now and y2>y2_now]
        x1_new = max(x1_list) if len(x1_list) else 0

        x2_list = [
            x1 for x1, y1, x2, y2 in boxes if x2 > x1_now and y2 > y2_now
        ]
        x2_new = min(x2_list) if len(x2_list) else (image_weight - 1)

        y2_list = [
            y1 for x1, y1, x2, y2 in boxes if y1 > y2_now and x1 < x2_now
        ]
        y2_new = min(y2_list) if len(y2_list) else (image_height - 1)

        bottom_rect = (x1_new, y2_now, x2_new, y2_new)

        if not check_ok(bottom_rect, boxes):
            bottom_rect = (0, 0, 0, 0)

        # bottom_rect = repair_box_height(bottom_rect,image_height,max_box_height)
        bottom_rect = repair_box_weight(bottom_rect, image_weight, location)
        # draw_x1y1x2y2([bottom_rect],image_path,detect_path)
        # exit()

        # # 以检测框最上面那条边为bottom的最大矩形
        x1_list = [
            x2 for x1, y1, x2, y2 in boxes if x2 < x1_now and y1 < y1_now
        ]
        x1_new = max(x1_list) if len(x1_list) else 0

        y1_list = [
            y2 for x1, y1, x2, y2 in boxes
            if y2 < y1_now and (x2 > x1_now and x1 < x2_now)
        ]
        y1_new = max(y1_list) if len(y1_list) else 0
        # print(y1_list)

        x2_list = [
            x1 for x1, y1, x2, y2 in boxes
            if x1 > x2_now and (y1 < y2_now or y2 > y1_now)
        ]
        # print(x2_list)
        x2_new = min(x2_list) if len(x2_list) else (image_weight - 1)

        top_rect = (x1_new, y1_new, x2_new, y1_now)
        # print(top_rect)

        if not check_ok(top_rect, boxes):
            top_rect = (0, 0, 0, 0)

        # top_rect = repair_box_height(top_rect,image_height,max_box_height)
        top_rect = repair_box_weight(top_rect, image_weight, location)
        # draw_x1y1x2y2([top_rect], image_path, detect_path)
        # exit()
        # # 以检测框最左边那条边为right的最大矩形
        y1_list = [
            y2 for x1, y1, x2, y2 in boxes if y2 < y1_now and x1 < x1_now
        ]  #
        y1_new = max(y1_list) if len(y1_list) else 0

        x1_list = [x2 for x1, y1, x2, y2 in boxes if x2 < x1_now]
        x1_new = max(x1_list) if len(x1_list) else 0
        # print(x1_new)

        y2_list = [
            y1 for x1, y1, x2, y2 in boxes if y2 > y2_now and x2 < x2_now
        ]
        y2_new = min(y2_list) if len(y2_list) else (image_height - 1)

        left_rect = (x1_new, y1_new, x1_now, y2_new)
        if not check_ok(left_rect, boxes):
            left_rect = (0, 0, 0, 0)

        # left_rect = repair_box_height(left_rect,image_height,max_box_height)
        # left_rect = repair_box_weight(left_rect,image_weight,location)

        # draw_x1y1x2y2([left_rect],image_path,detect_path)
        # exit()

        # # 以检测框最右边那条边为left的最大矩形
        y1_list = [
            y2 for x1, y1, x2, y2 in boxes if y2 < y1_now and x2 > x2_now
        ]
        y1_new = max(y1_list) if len(y1_list) else 0

        x2_list = [
            x1 for x1, y1, x2, y2 in boxes if x1 > x2_now and y2 > y1_now
        ]
        x2_new = min(x2_list) if len(x2_list) else (image_weight - 1)

        y2_list = [
            y1 for x1, y1, x2, y2 in boxes if y1 >= y2_now and x2 > x2_now
        ]
        y2_new = min(y2_list) if len(y2_list) else (image_height - 1)

        right_rect = (x2_now, y1_new, x2_new, y2_new)

        if not check_ok(right_rect, boxes):
            right_rect = (0, 0, 0, 0)

        # print(max_box_height)
        # right_rect = repair_box_height(right_rect,image_height,max_box_height)
        # right_rect = repair_box_weight(right_rect,image_weight,location)
        # draw_x1y1x2y2([right_rect],image_path,detect_path)
        # break

        bottom_area = get_area(bottom_rect)
        top_area = get_area(top_rect)
        left_area = get_area(left_rect)
        right_area = get_area(right_rect)

        all_box_info.append({
            "box": bottom_rect,
            "area": bottom_area,
            "word_vertical": word_vertical_dict[0]
        })
        all_box_info.append({
            "box": top_rect,
            "area": top_area,
            "word_vertical": word_vertical_dict[1]
        })
        all_box_info.append({
            "box": left_rect,
            "area": left_area,
            "word_vertical": word_vertical_dict[2]
        })
        all_box_info.append({
            "box": right_rect,
            "area": right_area,
            "word_vertical": word_vertical_dict[3]
        })

    return all_box_info

def repair_box_weight0(box,image_weight,location='center'):

    if location not in ['center','left']:
        return box

    x1,y1,x2,y2 = box
    middle_x = image_weight//2

    if location == 'left' and x2>= middle_x:
        # 删除右边的内容
        middle_x = middle_x+5
        x2_new = min(middle_x,x2)
        return [x1,y1,x2_new,y2]
    elif location == 'center' and x2>= middle_x and x1<=middle_x:
        # 检测框在中间，并且左右不对称的情况，让左右对齐
        max_x = image_weight-1
        left_black = x1
        right_black = max_x-x2
        max_black = max(left_black,right_black)
        return [max_black,y1,(max_x-max_black),y2]

    return box

def repair_box_weight(box,image_weight,location='center'):

    x1,y1,x2,y2 = box
    middle_x = image_weight//2

    if location == 'center' and x2>= middle_x and x1<=middle_x:
        # 检测框在中间，并且左右不对称的情况，让左右对齐
        max_x = image_weight-1
        left_black = x1
        right_black = max_x-x2
        max_black = max(left_black,right_black)
        return [max_black,y1,(max_x-max_black),y2]

    return box

def repair_box_height(box,image_height,max_box_height,max_lines = 3):
    x1,y1,x2,y2 = box
    h = y2-y1
    max_box_height = max_box_height*max_lines
    if h>max_box_height:
        height_gap = h - max_box_height
        height_gap = height_gap/2
        return [x1,y1+height_gap,x2,y2-height_gap]
    else:
        return box

def get_max_box_height(boxes):
    max_box_height = 0
    for box in boxes:
        x1,y1,x2,y2 = box
        h = y2-y1
        if h > max_box_height:
            max_box_height = h
    return max_box_height

def get_image_size(image_path):
    """
    获取图片的宽度和高度。

    参数:
    image_path (str): 图片路径

    返回:
    tuple: 图片的宽度和高度，格式为 (width, height)
    """
    # 打开图片
    image = Image.open(image_path)

    # 获取图片的宽度和高度
    width, height = image.size

    return width, height

def reduce_box_height(boxes,threshold=3):
    # find max box
    # max_w = 0
    max_h = 0
    for box in boxes:
        x1,y1,x2,y2 = box
        h = y2 - y1
        if h>max_h:
            max_h = h
    new_boxes = []
    for box in boxes:
        x1,y1,x2,y2 = box
        h = y2 - y1
        if h > (max_h/threshold):
            new_boxes.append(box)
        # else:
        #     print(box)
    return new_boxes

def reduce_box_weight(boxes,threshold=3):
    # find max box
    max_w = 0
    # max_h = 0
    for box in boxes:
        x1,y1,x2,y2 = box
        w = x2 - x1
        if w>max_w:
            max_w = w
    new_boxes = []
    for box in boxes:
        x1,y1,x2,y2 = box
        w = x2 - x1
        if w > (max_w/threshold):
            new_boxes.append(box)
        # else:
        #     print(box)
    return new_boxes

def get_textbox_height_weight(image_path, font_path, font_size, text):
    # 打开图片
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.textbbox((0, 0), text, font=font)

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    return text_height, text_width

def wrap_text(text, width, font_size, font_path, image_path):
    """
    对给定的文本进行自动换行，并计算文本框的高度。

    :param text: 要换行的文本
    :param width: 文本框的宽度（单位：像素）
    :param font_size: 字体大小（单位：像素）
    :param font_path: 字体文件路径（例如：'arial.ttf'）
    :return: 换行后的文本和文本框的高度
    """

    # 分割文本
    lines = []
    current_line = ""
    words = list(text)  # 分割单词

    for word in words:
        # 尝试将单词添加到当前行
        test_line = current_line + word if current_line else word

        text_height, text_width = get_textbox_height_weight(image_path, font_path, font_size, test_line)

        if text_width <= width:
            # 如果测试行的宽度小于等于文本框宽度，则将单词添加到当前行
            current_line = test_line
        else:
            # 否则，将当前行添加到结果中，并开始新的一行
            lines.append(current_line.strip())
            current_line = word

    # 添加最后一行
    if current_line:
        lines.append(current_line.strip())
    
    final_text = '\n'.join(lines)
    text_height, text_width = get_textbox_height_weight(image_path, font_path, font_size, final_text)

    return lines, text_height, text_width

def draw_text_in_box(image_path, save_path, box, text, font_path, color, font_size, location='center', outline_color=(0, 0, 0),word_vertical='center'):
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    # 获取检测框的宽度和高度
    x1, y1, x2, y2 = box
    box_width = x2 - x1
    box_height = y2 - y1

    font = ImageFont.truetype(font_path, font_size)

    text_height, text_width = get_textbox_height_weight(image_path, font_path, font_size, text)

    if word_vertical=='top':
        text_y = y1
    elif word_vertical=='bottom':
        text_y = y1 + box_height - text_height
    else:
        text_y = y1 + (box_height - text_height) // 2  # 垂直居中

    text_lines = text.split('\n')
    for line in text_lines:

        text_height, text_width = get_textbox_height_weight(image_path, font_path, font_size, line)

        if location=='left':
            text_x = x1
        elif location=='right':
            text_x = x1 + (box_width - text_width)
        else:
            # center
            text_x = x1 + (box_width - text_width) // 2

        # 绘制描边
        outline_width = 3
        for offset_x in range(-outline_width, outline_width + 1):
            for offset_y in range(-outline_width, outline_width + 1):
                if offset_x == 0 and offset_y == 0:
                    continue  # 跳过中心点，避免重复绘制
                draw.text((text_x + offset_x, text_y + offset_y), line, font=font, fill=outline_color)

        # 绘制文字的填充颜色
        draw.text((text_x, text_y), line, font=font, fill=color)

        text_y += text_height

    # 保存处理后的图片
    image.save(save_path)

def draw_text_in_box_with_auto_split_lines(image_path, save_path, box, text, font_path, color, max_word_height, location='center', outline_color=(0, 0, 0),word_vertical='center'):
    """
    在图片的检测框中写入自适应大小的文字，并使其完全居中。支持自动换行，且每行文字高度不超过 max_word_height。

    参数:
    image_path (str): 图片路径
    save_path (str): 保存处理后图片的路径
    box (list): 检测框，格式为 [x1, y1, x2, y2]
    text (str): 要写入的文字
    font_path (str): 字体文件路径
    color (tuple): 文字颜色，格式为 (R, G, B)
    max_word_height (int): 每行文字的最大高度限制
    location (str): 文字对齐位置，可选值为 'center', 'left', 'right'
    outline_color (tuple): 文字描边颜色，格式为 (R, G, B)

    返回:
    None
    """
    # 打开图片
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    # 获取检测框的宽度和高度
    x1, y1, x2, y2 = box
    box_width = x2 - x1
    box_height = y2 - y1

    # 初始化字体高度
    font_size = max_word_height

    # 自适应调整字体大小，同时支持换行
    while True:
        if font_size<=1:
            break
        # 创建当前字体高度的字体对象
        wrapped_text = wrap_text(text, box_width, font_size, font_path)
        font_width, font_height = get_text_bbox(wrapped_text, font_path, font_size)
        if font_height > box_height:
            font_size -= 1
        else:
            break

    total_height = font_height

    text = "\n".join(wrapped_text)

    font = ImageFont.truetype(font_path, font_size)

    if word_vertical=='top':
        text_y = y1
    elif word_vertical=='bottom':
        text_y = y1 + box_height - total_height
    else:
        text_y = y1 + (box_height - total_height) // 2  # 垂直居中

    text_x = x1 + (box_width - (font.getbbox(wrapped_text[0])[2] - font.getbbox(wrapped_text[0])[0])) // 2
    # print(box)
    # print(text_x,text_y)

    # 绘制描边
    outline_width = 3
    for offset_x in range(-outline_width, outline_width + 1):
        for offset_y in range(-outline_width, outline_width + 1):
            if offset_x == 0 and offset_y == 0:
                continue  # 跳过中心点，避免重复绘制
            draw.text((text_x + offset_x, text_y + offset_y), text, font=font, fill=outline_color)

    # 绘制文字的填充颜色
    draw.text((text_x, text_y), text, font=font, fill=color)
    # 保存处理后的图片
    image.save(save_path)

def get_new_results(results,inner_pt=10):
    x1,y1,x2,y2 = results
    return [x1+inner_pt,y1+inner_pt,x2-inner_pt,y2-inner_pt]

def box_strategy(box_info_dict, location, image_weight, image_height, min_font_area, max_word_height, font_path, text):
    """
    {"box":box,"area": area,"word_vertical":"top/down/center"}
    """
    # print(box_info_dict)
    for index, item in enumerate(box_info_dict):
        box = item['box']
        x1,y1,x2,y2 = box
        middle_x = image_weight//2
        if location == 'left':
            # if x1 < middle_x and ((middle_x-x2) < (image_weight//3)):
            if x1 < middle_x and item['area'] >= min_font_area:
                item['area'] = item['area']*10

        if location == 'center':
            if x1 < middle_x and x2 > middle_x and item['area'] >= min_font_area and ((x2-middle_x)>(image_weight//4)):
                item['area'] = item['area']*10
            elif x1 < middle_x and x2 > middle_x and item['area'] >= min_font_area:
                item['area'] = item['area']*8

    # 按照 box_area 从大到小排序
    sorted_data = sorted(box_info_dict, key=lambda x: x["area"], reverse=True)

    final_item = sorted_data[0]

    return final_item['box'],final_item['word_vertical']

def get_max_font_size(image_path, box, text, font_path, max_font_size):
    # 打开图片
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    font_size = max_font_size  # 初始字体大小

    # 循环增加字体大小，直到文字超出检测框或者达到一个比较合理的上限
    while True:
        if font_size<=1:
            break
        font = ImageFont.truetype(font_path, font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if text_width <= (box[2] - box[0]) and text_height <= (box[3] - box[1]):
            break
        else:
            font_size -= 1  # 如果超出了，回退一个字号大小

    return font_size

def get_font_size_and_final_text(box,text,split_text,max_word_height,font_path, image_path):
    # 自动换行后行数是否变化，如果变化的话，有几行就保留split_text的几行
    # 获取检测框的宽度和高度
    x1, y1, x2, y2 = box
    box_width = x2 - x1
    box_height = y2 - y1

    # 初始化字体高度
    font_size = max_word_height

    # 自适应调整字体大小，同时支持换行
    while True:
        if font_size <=1:
            break
        # 创建当前字体高度的字体对象
        wrapped_text, text_height, text_width = wrap_text(text, box_width, font_size, font_path, image_path)
        if text_height > box_height:
            font_size -= 1
        else:
            break
    lines = len(wrapped_text)
    split_text_lines = split_text.split('\n')

    final_text = text

    if lines==1:
        final_text = text
    elif lines>=len(split_text_lines):
        final_text = split_text
    else:
        # 智能合并，贪心算法
        final_text_lines = merge_sentences(split_text_lines, lines)
        final_text = '\n'.join(final_text_lines)
    
    # 根据 final_text 找最佳font_size
    font_size = get_max_font_size(image_path, box, final_text, font_path, max_word_height)
    
    return font_size, final_text

def add_text(all_boxes,
             words_boxes,
             image_path,
             save_path,
             text,
             split_text,
             location,
             font_path,
             font_color,
             outline_color,
             detect_path=None,
             final_box_path=None):

    image_weight, image_height = get_image_size(image_path)
    max_word_height = get_max_box_height(words_boxes)
    
    # max_word_height = max(min(max_word_height,(image_weight // 10)),image_weight // 20)
    max_word_height = max((image_weight // 15), max_word_height)

    all_box_info = find_max_rectangles(all_boxes, image_weight, image_height,
                                       max_word_height, location, image_path,
                                       detect_path)

    # print(all_box_info)

    min_font_height = image_weight // 30
    min_font_weight = min_font_height * len(text) * 0.7
    min_font_area = min_font_height * min_font_weight
    final_box, final_word_vertical = box_strategy(all_box_info, location,
                                                  image_weight, image_height,
                                                  min_font_area,
                                                  max_word_height, font_path,
                                                  text)
    # print(final_word_vertical)
    # print("final_box 0 ", final_box)
    # 找到最佳 font_size & final_text_lines
    font_size, final_text = get_font_size_and_final_text(final_box,text,split_text,max_word_height,font_path, image_path)

    # set inner space & write to img
    inner_black_list = [35, 30, 25, 20, 10, 0]
    for inner_black in inner_black_list:
        new_final_box = get_new_results(final_box, inner_black)
        new_font_size = get_max_font_size(image_path, new_final_box, final_text, font_path,max_word_height)
        if new_font_size == font_size:
            final_box = new_final_box
            break
    
    top_inner_black = [35, 30, 25, 20, 10, 0]
    x1,y1,x2,y2 = final_box
    if final_word_vertical == 'top':
        for inner_black in top_inner_black:
            new_final_box = [x1,y1+inner_black,x2,y2]
            if not check_ok_one(new_final_box):
                break
            new_font_size = get_max_font_size(image_path, new_final_box, final_text, font_path,max_word_height)
            if new_font_size == font_size:
                final_box = new_final_box
                break
    
    if final_word_vertical == 'bottom':
        for inner_black in top_inner_black:
            new_final_box = [x1,y1,x2,y2-inner_black]
            if not check_ok_one(new_final_box):
                break
            new_font_size = get_max_font_size(image_path, new_final_box, final_text, font_path,max_word_height)
            if new_font_size == font_size:
                final_box = new_final_box
                break

    # print("final_box 1 ", final_box)

    if final_box_path:
        draw_x1y1x2y2([final_box], image_path, final_box_path)

    font_size = max(5,font_size)
    final_text = final_text.replace("。",'')
    draw_text_in_box(image_path, save_path, final_box, final_text, font_path,
                     font_color, font_size, location, outline_color,
                     final_word_vertical)

def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)  # 将 JSON 文件内容解析为 Python 字典
    return data

def get_font_path(font_style):
    # https://www.fonts.net.cn/fonts-zh/tag-xingkai-1.html
    if font_style=='cute':
        font_list = [
            "/Users/zengxin/Downloads/cute_ttf/RuanMengXiaoGuoDong-2.ttf",
        ]
        
    elif font_style=='hand writting':
        font_list = [
            "/Users/zengxin/Downloads/字魂白鸽天行体(商用需授权)/字魂白鸽天行体(商用需授权).ttf",

        ]
    else:
        font_list = [
            "/Users/zengxin/workspace/data/200_eval/font/YeZiGongChangShanHaiMingChao-2.ttf",
            "/Users/zengxin/workspace/data/200_eval/font/No.341-ShangShouSaTi-2.ttf", # 不错
            "/Users/zengxin/workspace/data/200_eval/font/TianShiYanTiDaZiKu-1.ttf", # 不错
            "/Users/zengxin/workspace/data/200_eval/font/WenYue-JuJiuWuTi-J-2.otf",
            "/Users/zengxin/workspace/data/200_eval/font/WenYue-ZHJXinWeiTi-GBK-2.otf", # 不错
            "/Users/zengxin/workspace/data/200_eval/font/SentyCloud-2.ttf",
            "/Users/zengxin/workspace/data/200_eval/font/ZiHunBianTaoTi-2.ttf",
        ]

    return random.choice(font_list)

def get_color_rgb(font_color):
    if '/' in font_color:
        font_color = font_color.split("/")
    if type(font_color)==list:
        font_color = font_color[0]
    # https://www.sojson.com/rgb.html
    color_dict={
        "white":(255,255,255),
        "green":(240,255,240), # 浅绿色
        "yellow":(255,250,205), # 浅黄色
        "black":(0,0,0),
        "red":(255,69,0), # 蕃茄红
        "purple":(171,130,255), # MediumPurple1
        "blue":(191,239,255), # 浅蓝色 	LightBlue1
        "grey":(207,207,207), # 	gray81
        "pink":(255,225,255),
    }
    # print("font_color",font_color)
    if font_color in color_dict:
        return color_dict[font_color]
    else:
        # black
        return (0,0,0)

def contains_chinese(text):
    """
    判断字符串中是否包含中文字符。

    :param text: 要检查的字符串
    :return: 如果包含中文字符，返回 True；否则返回 False
    """
    for char in text:
        if 'CJK' in unicodedata.name(char, ''):  # 检查字符是否属于 CJK 字符
            return True
    return False

if __name__ == "__main__":

    orig_img_dir = "/Users/zengxin/workspace/data/200_eval/origin_data"
    output_dir = "/Users/zengxin/workspace/data/200_eval/output/1213/split_results"
    boxes_dir = "/Users/zengxin/workspace/data/200_eval/output/1212v2//boxes"
    response_dir = "/Users/zengxin/workspace/data/200_eval/output/1213/split_response"
    file_name_list = os.listdir(orig_img_dir)

    for p in [output_dir]:
        if not os.path.exists(p):
            os.makedirs(p)

    for file_name in tqdm(file_name_list):
        # print("file_name",file_name)

        if not file_name.endswith(".jpg"):  # 检查文件是否以 ".mp4" 结尾
            continue
        
        # if file_name != '102_lQh-ypft_98.jpg':
        #     continue

        image_path = os.path.join(orig_img_dir,file_name)

        new_file_name = file_name.replace(".jpg",".zh.jpg")
        save_path = os.path.join(output_dir, new_file_name)

        # if os.path.exists(save_path):
        #     # print(save_path)
        #     continue

        # print(file_name)

        words_boxes_path = os.path.join(boxes_dir, file_name+".ocr_boxes.json")
        human_face_box_path = os.path.join(boxes_dir, file_name+".human_face_boxes.json")
        cartoon_face_box_path = os.path.join(boxes_dir, file_name+".cartoon_face_boxes.json")

        # print(image_path)
        # print(words_boxes_path)
        # exit()
        if (not os.path.exists(words_boxes_path)) or (not os.path.exists(human_face_box_path) or (not os.path.exists(cartoon_face_box_path))):
            # print(words_boxes_path)
            print(file_name,' box not exists')
            continue
            # exit()

        words_boxes = read_json(words_boxes_path)['box']
        human_face_box = read_json(human_face_box_path)['box']
        cartoon_face_box = read_json(cartoon_face_box_path)['box']

        human_face_box = reduce_box_weight(human_face_box)
        cartoon_face_box = reduce_box_weight(cartoon_face_box)

        words_boxes = reduce_box_height(words_boxes,10)
        words_boxes = reduce_box_weight(words_boxes,10)

        all_boxes = words_boxes + human_face_box + cartoon_face_box

        # print(all_boxes)
        tmp_save_path = os.path.join(output_dir,file_name+'.boxes.png')
        draw_x1y1x2y2(all_boxes,image_path,tmp_save_path)

        response_path = os.path.join(response_dir, file_name + ".pic_title.json")
        # print(response_path)
        if not os.path.exists(response_path):
            print(response_path," not exists")
            continue

        response = read_json(response_path)
        print(response)

        if 'title' not in response:
            continue

        if response['title'] == 'None':
            continue

        if contains_chinese(response['title']):
            continue

        if 'trans' not in response:
            continue

        if 'split_zh' not in response:
            response['split_zh'] = response['trans']
        
        if not contains_chinese(response['split_zh']):
            response['split_zh'] = response['trans']

        text = response['trans']
        split_text = response['split_zh']
            
        location = response['location']
        # print("location ",location)

        if 'font_style' in response:
            font_path = get_font_path(response['font_style'])
        else:
            font_path = get_font_path('normal')
        
        if 'font_color' in response:
            font_color = get_color_rgb(response['font_color'])
        else:
            font_color = get_color_rgb('white')

        outline_color = [(255-i) for i in font_color]
        outline_color = tuple(outline_color)

        detect_path = os.path.join(output_dir,file_name+'.detect.png')
        final_box_path = os.path.join(output_dir,file_name+'.final_box.png')
        add_text(all_boxes,words_boxes,image_path,save_path,text, split_text,location,font_path,font_color,outline_color,detect_path,final_box_path)

        # exit()
