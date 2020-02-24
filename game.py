import pygame as p
import math as m
import os
import re
import random as r

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
CYAN = (0,255,255)
MAGENTA = (255,0,255)
YELLOW = (255,255,0)
TRANSPARENCY_COLOUR = (0,126,126)


p.init()
WIDTH = 704
HEIGHT = 704
S_WIDTH = WIDTH
S_HEIGHT = HEIGHT
LEVEL_SCALE_X = 50
LEVEL_SCALE_Y = 50
screen = p.display.set_mode((S_WIDTH, S_HEIGHT))

TW = 50
TH = 50

main_dir = "files/"
gfx_dir = main_dir+"gfx/"
level_dir = main_dir+"level/"
sound_dir = main_dir+"sound/"

p.display.set_caption("Bunker Builder")

CHUNK_WIDTH = 80
CHUNK_HEIGHT = 80
CHUNK_LOAD_DISTANCE = 200

MAX_TICK_RATE = 60
clock = p.time.Clock()

entities = []
creatures = []
animations = []
animation_systems = []
projectiles = []
effects = []
events = []
interface_components = []
buttons = []
overlays = []

structures = []
workers = []
icons = []
explosions = []

active_levels = []

arial_font = p.font.SysFont("arial", 25)
observe_font = p.font.SysFont("arial", 20)
icon_font = p.font.SysFont("arial", 18)
HUD_font = p.font.SysFont("consolas", 40)
money_font = p.font.SysFont("arial", 40)
cost_font = p.font.SysFont("arial", 20)
timer_font = p.font.SysFont("consolas", 30)

GRAVITY = 2
DEPTH_COST_MULTIPLIER = 0.05
MAX_MONEY = 3500

free_build = False

keys, mx, my, ml, mm, mr =\
[], 0, 0, False, False, False

#game state
selected_tile = None
current_state = "start"
current_substate = "build"
selected_build_structure = None
selected_structure = None
selected_worker = None

p.mixer.init()
sound_dict = {}
def load_sound_dict():
    #iterate through sound files in dir_sound directory
    for file in os.listdir(sound_dir):
        #remove file extension to get sound name
        sound_name = file[:-4]
        #create sound object
        sound = p.mixer.Sound(sound_dir+file)
        sound_dict.update({sound_name:sound})
load_sound_dict()

current_music = None
def set_music(name):
    global current_music
    if current_music != name:
        p.mixer.music.stop()
        current_music = name
        p.mixer.music.load(sound_dir+name+".ogg")
        p.mixer.music.play(-1)

def play_sound(name):
    sound_dict[name].play()

#helper functions
def nmx(x):
    normalised_x = x/WIDTH
    return normalised_x

def nmy(y):
    normalised_y = y/HEIGHT
    return normalised_y

def dnmx(x):
    denormalised_x = x*WIDTH
    return denormalised_x

def dnmy(y):
    denormalised_y = y*HEIGHT
    return denormalised_y

def get_distance(x1, y1, x2, y2):
    x = x2-x1
    y = y2-y1
    dist = ((x**2) + (y**2))**0.5
    return dist

def get_angle(x1, y1, x2, y2):
    x = x2-x1
    y = y2-y1
    angle = m.atan2(y,x)
    return angle

def interpolate_between_values(v1, v2, amount):
    difference = v2-v1
    interpolated_value = v1+(difference*amount)
    return interpolated_value

#turn a raw string formatted like this
#"""
#section one:
#line1
#line2
#section one:
#line 1
#"""
#into a dictionary where each value is a list
def split_string_into_sections(raw_string, split_text, lines=True):
    split_finder_pattern = re.compile(split_text+" [a-zA-Z0-9_]+:")
    
    sections_names = [n[len(split_text)+1:-1] for n in re.findall(split_finder_pattern, raw_string)]
    sections_data = re.split(split_finder_pattern, raw_string)[1:]

    #split into lines
    if lines:
        sections_lines = []
        for section_data in sections_data:
            section_lines = [l for l in section_data.split("\n") if l]
            sections_lines.append(section_lines)
        sections = dict(zip(sections_names, sections_lines))
    #split into raw strings
    else:
        sections = dict(zip(sections_names, sections_data))
    
    return sections

#turn a string like this
#key1=value1
#key2=value2
#key3=value3
#into a dictionary
def turn_string_into_dict(string_data):
    #setup tile_key dictionary
    dictionary = {}
    
    #split raw_key_data into lines, with each line containing a tile character and a tile name
    string_data_lines = string_data.split("\n")

    #create tile key
    for item_string in string_data_lines:
        #ignore empty key_strings
        if item_string and not item_string.isspace():
            key, value = item_string.split("=")
            dictionary.update({key:value})

    return dictionary

def load_surface(path):
    surface = p.image.load(gfx_dir+path).convert()
    return surface

def get_surface(graphics):
    if type(graphics) == Animation or type(graphics) == Animation_System:
        surface = graphics.get_current_frame()
    else:
        surface = graphics
    return surface

def get_max_population():
    max_pop = 2
    for structure in structures:
        if type(structure) == Housing:
            max_pop += 4

    return max_pop

class Event():
    def __init__(self, timer):
        self.timer = timer
        events.append(self)
        
    def update(self):
        self.timer -= 1
        if self.timer == 0:
            self.end()

    def end(self):
        self.delete()

    def delete(self):
        events.remove(self)

class Delete_Event(Event):
    def __init__(self, entity, timer):
        Event.__init__(self, timer)
        self.entity = entity

    def end(self):
        Event.end(self)
        self.entity.delete()

class Move_Event(Event):
    def __init__(self, entity, dx, dy, timer):
        Event.__init__(self, timer)
        self.entity = entity
        self.ax = dx/timer
        self.ay = dy/timer

    def update(self):
        Event.update(self)
        self.entity.move(self.ax, self.ay)

class Teleport_Event(Event):
    def __init__(self, entity, ex, ey, timer):
        Event.__init__(self, timer)
        self.entity = entity
        self.sx = self.entity.x
        self.sy = self.entity.y
        self.ex = ex
        self.ey = ey
        self.max_timer = self.timer

    def update(self):
        Event.update(self)
        progress = 1-(self.timer/self.max_timer)
        x = interpolate_between_values(self.sx, self.ex, progress)
        y = interpolate_between_values(self.sy, self.ey, progress)
        self.entity.x = x
        self.entity.y = y

class Overlay(Event):
    def __init__(self, timer, colour):
        Event.__init__(self, timer)
        overlays.append(self)
        self.surface = p.Surface((WIDTH, HEIGHT))
        self.surface.fill(colour)
        self.surface.set_alpha(255)

    def update(self):
        Event.update(self)
        progress = 1-(self.timer/self.max_timer)
        alpha = int(255*progress)
        self.surface.set_alpha(alpha)

    def draw(self):
        screen.blit(self.surface, (0,0))

    def delete(self):
        Event.delete(self)
        overlays.remove(self)

class Interface_Component():
    def __init__(self, rect, active_states):
        self.rect = rect
        self.active_states = active_states
        interface_components.append(self)

        self.active = False

    def update(self):
        self.set_active()

    def set_active(self):
        self.active = current_state in self.active_states

    def draw(self):
        pass        

class Decoration(Interface_Component):
    def __init__(self, rect, graphics, active_states):
        Interface_Component.__init__(self, rect, active_states)
        self.graphics = graphics

        if type(self.graphics) == p.Surface:
            self.graphics = p.transform.scale(self.graphics, (self.rect.w, self.rect.h))
        
    def update(self):
        Interface_Component.update(self)
        if self.active:
            self.surface = get_surface(self.graphics)

    def draw(self):
        Interface_Component.draw(self)
        if self.surface.get_size() != (self.rect.w, self.rect.h):
            surface = p.transform.scale(self.surface, (self.rect.w, self.rect.h))
        else:
            surface = self.surface
        screen.blit(surface, self.rect)

class Info_Window_Border(Decoration):
    def __init__(self, rect):
        graphics = load_surface("info_window_border.png")
        Decoration.__init__(self, rect, graphics, ["main"])

    def update(self):
        Decoration.update(self)
        if self.active and current_substate not in ["observe", "workers", "worker_assign"]:
            self.active = False
        

class Button(Interface_Component):
    def __init__(self, name, rect, pressed_surface, unpressed_surface, active_states, active_substates, highlighted_colour=GREEN, highlighted_thickness=4):
        Interface_Component.__init__(self, rect, active_states)
        self.name = name
        self.pressed_surface = p.transform.scale(pressed_surface, (self.rect.w, self.rect.h))
        self.unpressed_surface = p.transform.scale(unpressed_surface, (self.rect.w, self.rect.h))
        self.highlighted_colour = highlighted_colour
        self.highlighted_thickness = highlighted_thickness
        
        self.highlighted = False
        self.pressed = False
        self.active_substates = active_substates

        buttons.append(self)

    def update(self):
        Interface_Component.update(self)
        if self.active and self.name == "start_button":
            if menu_slides.slide_index != 0:
                self.active = False
            
        if self.active and self.active_substates != False:
            if not current_substate in self.active_substates:
                self.active = False
            
        if self.active:
            self.set_pressed()
            if self.pressed:
                self.surface = self.pressed_surface
            else:
                self.surface = self.unpressed_surface

        if self.name == "worker_assign_button":
            if not selected_worker:
                self.active = False

    def check_highlighted(self):
        if self.active:
            if self.rect.collidepoint((mx, my)):
                return True
            else:
                return False

    def set_pressed(self):
        if self.rect.collidepoint((mx, my)):
            self.highlighted = True
            if ml:
                if not self.pressed:
                    self.press()
                self.pressed = True
            else:
                self.pressed = False
        else:
            self.highlighted = False

    def press(self):
        global current_state, current_substate
        play_sound("select")
        if self.name == "start_button":
            
            current_state = "main"
            set_music("music_main")
            reset()
            menu_slides.slide_index = 0

        if self.name == "worker_button":
            current_substate = "workers"
        elif self.name == "build_button":
            current_substate = "build"
        elif self.name == "observe_button":
            current_substate = "observe"
        elif self.name == "demolish_button":
            current_substate = "demolish"
        elif self.name == "worker_assign_button":
            if selected_worker:
                current_substate = "worker_assign"

    def draw(self):
        Interface_Component.draw(self)
        screen.blit(self.surface, self.rect)
        if self.highlighted:
            p.draw.rect(screen, self.highlighted_colour, self.rect, self.highlighted_thickness)
            
class Slides(Interface_Component):
    def __init__(self, rect, slides, active_states, slide_index=0):
        Interface_Component.__init__(self, rect, active_states)
        self.slides = []
        for slide in slides:
            if type(slide) == p.Surface:
                slide = p.transform.scale(slide, (self.rect.w, self.rect.h))
            elif type(slide) == str:
                slide = p.transform.scale(p.image.load(gfx_dir+slide).convert(), (self.rect.w, self.rect.h))
            self.slides.append(slide)
            
        self.slide_index = slide_index

    def progress(self, amount):
        self.slide_index = (self.slide_index+amount)%len(self.slides)

    def update(self):
        Interface_Component.update(self)
        if self.active:
            self.surface = self.slides[self.slide_index]

    def draw(self):
        Interface_Component.draw(self)
        screen.blit(self.surface, self.rect)

#WIP  
class Text_Box(Interface_Component):
    def __init__(self, rect, font, text, active_states, colour=BLACK, background_colour=None, border_colour=None, border_width=4):
        Interface_Component.__init__(self, rect, active_states)

        self.font = font
        self.colour = colour
        self.background_colour = background_colour
        self.border_colour = border_colour
        self.border_width=border_width
        
        self.text = text
        self.old_text = self.text
        self.set_text(self.text)

    def update(self):
        Interface_Component.update(self)
        if self.old_text != self.text:
            self.set_text(self.text)
            
        self.old_text = self.text

    def set_text(self, text):
        lines = []
        text_height = self.font.size(text)[1]
        
        s = 0
        newline_needed = False
        finished = False
        e = 0
        while not finished:
            while not newline_needed:
                if s+e >= len(text):
                    newline_needed = True
                    finished = True
                else:
                    current_line = text[s:s+e+1]
                    width = self.font.size(current_line)[0]
                    if width >= self.rect.w:
                        newline_needed = True
                    else:
                        e += 1
                    
            lines.append(text[s:s+e])
            newline_needed = False
            s = s+e

        self.surface = p.Surface((self.rect.w, self.rect.h))
        

            
        if self.background_colour:
            self.surface.fill(self.background_colour)
        else:
            if self.colour == TRANSPARENCY_COLOUR:
                c_key = BLACK
            else:
                c_key = TRANSPARENCY_COLOUR
                
            self.surface.fill(c_key)
            self.surface.set_colorkey(c_key)
                
            
        if self.border_colour:
            p.draw.rect(self.surface, self.border_colour, self.surface.get_rect(), self.border_width*2)
        
        
        y = 0
        for line in lines:
            line_text = self.font.render(line, False, self.colour)
            self.surface.blit(line_text, (0,y) )
            y += text_height

    def draw(self):
        screen.blit(self.surface, self.rect)
        
class Build_Option(Button):
    def __init__(self, name, surface, build_menu):
        self.build_menu = build_menu
        
        x = self.build_menu.rect.x+self.build_menu.option_spacing+((self.build_menu.option_width+self.build_menu.option_spacing)*len(self.build_menu.build_options))
        y = int(self.build_menu.rect.centery-(self.build_menu.option_height/2))
        rect = p.Rect(x,y,self.build_menu.option_width,self.build_menu.option_height)
        Button.__init__(self, name, rect, surface, surface, ["main"], ["build"])

        
        
        self.build_menu.build_options.append(self)

    def press(self):
        global selected_build_structure
        Button.press(self)
        if self.name == "corridor":
            selected_build_structure = corridor_template
        elif self.name == "vacuum tube":
            selected_build_structure = vacuum_tube_template
        elif self.name == "ventilator":
            selected_build_structure = ventilator_template
        elif self.name == "generator":
            selected_build_structure = generator_template
        elif self.name == "farm":
            selected_build_structure = farm_template
        elif self.name == "mine":
            selected_build_structure = mine_template
        elif self.name == "housing":
            selected_build_structure = housing_template

class Build_Menu(Interface_Component):
    def __init__(self, rect, surface, option_width, option_height, option_spacing):
        Interface_Component.__init__(self, rect, ["main"])
        self.surface = p.transform.scale(surface, (self.rect.w, self.rect.h))
        
        self.build_options = []

        self.option_width = int(option_width)
        self.option_height = int(option_height)
        self.option_spacing = int(option_spacing)

    def update(self):
        Interface_Component.update(self)
        if self.active and not current_substate == "build":
            self.active = False
            
        if self.active:
            for build_option in self.build_options:
                build_option.set_pressed()

    def draw(self):
        screen.blit(self.surface, self.rect)
        for build_option in self.build_options:
            build_option.draw()         

class Level():
    def __init__(self, active, x=0, y=0):
        self.active = active
        if self.active:
            self.activate()

        self.x = x
        self.y = y

    def activate(self):
        self.active = True
        active_levels.append(self)

    def deactivate(self):
        self.active = False
        active_levels.remove(self)

class Mask_Level(Level):
    def __init__(self, path, x=0, y=0, level_scale_x=1, level_scale_y=1, active=True):
        Level.__init__(self, active, x=x, y=y)
        
        path = level_dir+path

        

        unscaled_level_surface = p.image.load(path+".png")
        unscaled_collision_surface = p.image.load(path+"_collision.png")
        unscaled_rect = unscaled_level_surface.get_rect()
        
        level_surface = p.transform.scale(unscaled_level_surface, (unscaled_rect.w*level_scale_x, unscaled_rect.h*level_scale_y)) 
        collision_surface = p.transform.scale(unscaled_collision_surface, (unscaled_rect.w*level_scale_x, unscaled_rect.h*level_scale_y)) 

        self.chunks = []
        self.active_chunks = []

        self.rect = level_surface.get_rect()
        for x in range( m.ceil(self.rect.width/CHUNK_WIDTH) ):
            cx = x*CHUNK_WIDTH
            for y in range( m.ceil(self.rect.height/CHUNK_HEIGHT) ):
                cy = y*CHUNK_HEIGHT

                rect = p.Rect(cx, cy, CHUNK_WIDTH, CHUNK_HEIGHT)        
                self.chunks.append(Chunk(self, rect, level_surface, collision_surface))

    def set_active_chunks(self, point):
        self.active_chunks.clear()
        
        for chunk in self.chunks:
            center = chunk.rect.center
            distance = get_distance(point[0], point[1], center[0], center[1])

            if distance <= CHUNK_LOAD_DISTANCE:
                self.active_chunks.append(chunk)

    def draw(self, camera):
        for chunk in self.active_chunks:
            camera.draw_transformed_surface(chunk.collision_surface, chunk.rect)

class Chunk():
    def __init__(self, level, rect, surface, collision_surface):
        self.level = level
        
        self.rect = rect
        
        self.surface = p.Surface((self.rect.width, self.rect.height))
        self.surface.blit(surface, (0,0), self.rect)

        self.collision_surface = p.Surface((self.rect.width, self.rect.height))
        self.collision_surface.blit(collision_surface, (0,0), self.rect)

        self.mask = p.mask.from_threshold(self.collision_surface, (0,0,0,255), (255,255,255,255))

    def check_collision(self, rect, mask):
        if self.rect.move(self.level.x, self.level.y).colliderect(rect):
            collision_offset = (rect.x-(self.level.x+self.rect.x), rect.y-(self.level.y+self.rect.y))
            collision = self.mask.overlap(mask, collision_offset )

            return collision
        else:
            return False

class Tile_Level(Level):
    def __init__(self, w, h, tw, th, x=0, y=0, active=True):
        Level.__init__(self, active, x=x, y=y)


        self.tw = tw
        self.th = th

        self.t_width = w
        self.t_height = h

        self.tiles = self.build_level_tiles(self.t_width, self.t_height)

        
        self.width = self.t_width*self.tw
        self.height = self.t_height*self.th

        self.rect = p.Rect(0,0,self.width,self.height)       

        
    def build_level_tiles(self, width, height):

        #create 2D list of tiles
        tiles = []
        for x in range(width):
            tiles.append([])
            for y in range(height):
                #create tile
                tile_choices = (["dirt"]*35)+ (["gold"]*2) + (["diamonds"]*2) + (["fossil"]*1) + (["empty"]*0) + (["rock"]*0)
                tile_name = r.choice(tile_choices)
                
                tile = Tile(self, x, y, tile_name)
                tiles[-1].append(tile)

        return tiles

    def check_collision(self, rect, full=False):
        solid_tiles = []
        
        sx = int((rect.x-self.x)/self.tw)-2
        sy = int((rect.y-self.y)/self.th)-2
        ex = sx+int(rect.width/self.tw)+4
        ey = sy+int(rect.height/self.th)+4
        for x in range(sx,ex):
            for y in range(sy,ey):
                if x >= 0 and y >= 0 and x < self.width/self.tw and y < self.height/self.th:
                    tile = self.tiles[x][y]
                    
                    if tile.solid:
                        solid_tiles.append(tile)

        if full:
            colliding_tiles = []
            
        for tile in solid_tiles:
            if tile.rect.move((tile.level.x, tile.level.y)).colliderect(rect):
                if full:
                    colliding_tiles.append(tile)
                else:
                    return tile
                    
        if full:
            return colliding_tiles

    def draw(self, camera):
        sx = int((camera.screen_x-self.x)/self.tw)
        sy = int((camera.screen_y-self.y)/self.th)
        ex = sx+int(camera.width/self.tw)+1
        ey = sy+int(camera.height/self.th)+1
        for x in range(sx,ex):
            for y in range(sy,ey):
                if x >= 0 and y >= 0 and x < self.width/self.tw and y < self.height/self.th:
                    tile = self.tiles[x][y]
                    tile.draw(camera)

class Tile():
    def __init__(self, level, x, y, name):
        self.level = level
        self.tx = x
        self.ty = y
        self.x = self.tx*level.tw
        self.y = self.ty*level.th
        self.rect = p.Rect(self.x, self.y, level.tw, level.th)


        self.name = name
        self.solid = False
        self.can_damage = False

        #find sprite
        if self.name == "dirt":
            sprite_index = 0
            self.solid = True
            self.can_damage = True
            self.max_health = 20
        if self.name == "gold":
            sprite_index = 3
            self.solid = True
            self.can_damage = True
            self.max_health = 25
        if self.name == "diamonds":
            sprite_index = 4
            self.solid = True
            self.can_damage = True
            self.max_health = 25
        if self.name == "fossil":
            sprite_index = 5
            self.solid = True
            self.can_damage = True
            self.max_health = 25
            
        elif self.name == "empty":
            sprite_index = 1
            self.max_health = 0
            
        elif self.name == "rock":
            sprite_index = 2
            self.solid = True
            self.can_damage = True
            self.max_health = 35

        self.graphics = tile_spritesheet.sprites[sprite_index][0]
        self.damaged_graphics = tile_spritesheet.sprites[sprite_index][1]
        self.health = self.max_health

    def change_health(self, amount):
        self.health += amount
        if self.health > self.max_health:
            self.health = self.max_health
        elif self.health <= 0:
            self.health = 0
            self.delete()

    def delete(self):
        self.name = "empty"
        self.graphics = tile_spritesheet.sprites[1][0]
        self.max_health = 0
        self.can_damage = False
        self.solid = False

    def draw(self, camera):
        if self.health > self.max_health/2 or self.name == "empty":
            surface = get_surface(self.graphics)
        else:
            surface = get_surface(self.damaged_graphics)
        camera.draw_transformed_surface(surface, self.rect.move((self.level.x, self.level.y)).inflate(2,2))

    def draw_status(self, x, y, font=observe_font):
        text_height = font.size("A")[1]
        name_text = font.render(self.name, False, WHITE)
        screen.blit(name_text, (x,y) )
        
        y += text_height
        if self.can_damage:
            health_fraction = self.health/self.max_health
            if health_fraction == 1:
                colour = CYAN
            elif health_fraction >= 0.7:
                colour = GREEN
            elif health_fraction >= 0.3:
                colour = YELLOW
            else:
                colour = RED
            
            health_string = "Health: "+str(self.health)+"/"+str(self.max_health)
            health_text = font.render(health_string, False, colour)
            screen.blit(health_text, (x,y))

        if self.name in ["gold", "diamonds", "fossil"]:
            y += text_height
            if self.name == "gold":
                value = 200
            elif self.name == "diamonds":
                value = 300
            elif self.name == "fossil":
                value = 400
            value_string = "Value: $"+str(value)
            value_text = font.render(value_string, False, WHITE)
            screen.blit(value_text, (x,y))


#Animation class for holding animations
class Animation():
    def __init__(self, frames, max_animation_timer):
        self.frames = frames
        
        #animation speed is based on the amount of game frames per animation frame
        #a value of zero means that animation does not update
        if max_animation_timer == 0:
            self.animation_speed = 0
        else:
            self.animation_speed = len(self.frames)/max_animation_timer
        self.progress = 0

        #add to list of animations
        animations.append(self)


    def update(self):
        #progress animation
        self.progress += self.animation_speed
        
        #reset animation
        if self.progress >= len(self.frames):
            self.progress -= len(self.frames)

    def get_current_frame(self):
        #get frame
        frame_no = int(self.progress)
        frame = self.frames[frame_no]
        return frame

#Animation_System class for holding multiple animations
class Animation_System():
    def __init__(self, spritesheet, anim_id_dict, current_animation_name, anim_timer):
        #generate animations for this Animation_System object
        self.animations = {name:spritesheet.generate_animation(anim_id, anim_timer) for name,anim_id in anim_id_dict.items()}

        #the currently playing animation
        self.current_animation_name = current_animation_name

        animation_systems.append(self)

    #set the current animation by name
    def set_animation(self, name):
        if self.current_animation_name != name:
            self.animations[self.current_animation_name].progress = 0
        self.current_animation_name = name

    #progress current animation
    def update(self):
        self.animations[self.current_animation_name].update()

    #get current frame of current animation
    def get_current_frame(self):
        return self.animations[self.current_animation_name].get_current_frame()

    #get progress of current animation
    def get_progress(self):
        return self.animations[self.current_animation_name].progress

#Spritesheet class for holding graphical data
class Spritesheet():
    def __init__(self, name, sprite_width, sprite_height, transparency_pixel=None, transparency_colorkey=None):
        path = gfx_dir+name
        self.surface = p.image.load(path)

        self.sprites = []

        surface_width, surface_height = self.surface.get_width(), self.surface.get_height()
        #iterate though individual sprite sections in the spritesheet surface
        #set up animations
        for sprite_y in range(int(surface_height/sprite_height)):
            y = sprite_y*sprite_height
            animation_frames = []
            
            for sprite_x in range(int(surface_width/sprite_width)):
                x = sprite_x*sprite_width

                if transparency_pixel and self.surface.get_at((x,y)) == transparency_pixel:
                    transparent = True
                    
                else:
                    transparent = False

                if transparent:
                    surface = p.Surface((sprite_width, sprite_height), flags=p.SRCALPHA).convert_alpha()
                else:
                    surface = p.Surface((sprite_width, sprite_height)).convert()

                if transparency_colorkey:
                    surface.set_colorkey(transparency_colorkey)

                #this is the area of the spritesheet that will be turned into the sprite
                spritesheet_area = p.Rect(x, y, sprite_width, sprite_height)

                #create the sprite surface
                surface.blit(self.surface, (0,0), spritesheet_area)
                if transparent:
                    surface.set_at((0,0), (0,0,0,0))
                    
                animation_frames.append(surface)

            #store animation frames
            self.sprites.append(animation_frames)

    #generate animation using frames from a particular animation ID
    def generate_animation(self, anim_id, anim_timer):
        animation = Animation(self.sprites[anim_id], anim_timer)
        return animation

def check_collision(rect, collision_mask, collision_dict, exceptions, full=False):
    if full:
        colliding = []
    else:
        colliding = False

    #check for collisions with levels
    if collision_dict["levels"]:
        for level in active_levels:
            if type(level) == Mask_Level:
                for chunk in level.active_chunks:
                    if chunk.check_collision(rect, collision_mask):
                        if full:
                            colliding.append(chunk)
                        else:
                            colliding = chunk
                            break

            elif type(level) == Tile_Level:
                tile_collision = level.check_collision(rect, full=full)
                if tile_collision:
                    if full:
                        colliding += tile_collision
                    else:
                        colliding = tile_collision
                        break

    #check for collision with structures
    if collision_dict["structures"]:
        for structure in structures:
            if structure.rect.colliderect(rect):
                if full:
                    colliding.append(structure)
                else:
                    colliding = structure
                    break

    if collision_dict["structures_travel"]:
        for structure in structures:
            if type(structure) != Vacuum_Tube and structure.rect.colliderect(rect):
                if full:
                    colliding.append(structure)
                else:
                    colliding = structure
                    break
        
    #check for collision with other creatures
    for creature in creatures:
        if creature not in exceptions and creature.solid and creature.rect.colliderect(rect):
            if collision_dict["creatures"] or (type(creature) == Player and collision_dict["player"]):
                if full:
                    colliding.append(creature)
                else:
                    colliding = creature
                    break

    return colliding

#abstract parent class for entities
class Entity():
    def __init__(self, rect, vx=0, vy=0, vx_keep=0.9, vy_keep=0.9, max_v=3, parent=None, solid=False, visible=True, cw=1, ch=1, collision_dict={"levels":True, "structures":False, "structures_travel":False, "creatures":False, "player":False, "border":False}, collision_exceptions=[]):
        self.rect = rect
        #x, y, width, height attributes are needed since pygame rect can only store int values
        self.x = self.rect.x
        self.y = self.rect.y

        self.width = self.rect.w
        self.height = self.rect.h
        self.cw = cw
        self.ch = ch

        self.old_width = self.width
        self.old_height = self.height
        self.update_mask()

        #collision attributes
        self.solid = solid
        self.collision_dict = collision_dict
        self.collision_exceptions = collision_exceptions

        #velocity attributes
        self.vx = vx
        self.vy = vy
        self.vx_keep = vx_keep
        self.vy_keep = vy_keep
        self.max_v = max_v

        #parent/children attributes
        if parent:
            self.set_parent(parent)
        self.children = []

        self.visible = visible
        self.surface = None

        entities.append(self)

    def set_parent(self, parent):
        self.parent = parent
        self.parent.children.append(self)

    #make the centerpoint of the entity a given point
    def center(self, center):
        self.rect.center = center
        self.x = self.rect.x
        self.y = self.rect.y

        
    #set rect values based off of position and dimensions
    def update_rect(self):
        self.rect.x = self.x
        self.rect.y = self.y

    def update_mask(self):
        self.rect.w = self.width
        self.rect.h = self.height
        self.collision_mask = p.mask.Mask((self.width, self.height))
        self.collision_mask.fill()

    def update(self):
        if self.width != self.old_width or self.height != self.old_height:
            self.update_mask()
            
        old_x = self.x
        old_y = self.y

        self.update_rect()
        #update position and velocity
        self.move(self.vx, self.vy)
        self.vx *= self.vx_keep
        self.vy *= self.vy_keep

        #if velocity is very low set it to 0
        if abs(self.vx) <= 0.01:
            self.vx = 0
        if abs(self.vy) <= 0.01:
            self.vy = 0

        #gradient must be maintained while capping velocity
        direction = get_angle(0, 0, self.vx, self.vy)
        v_mag = get_distance(0,0,self.vx,self.vy)
            
        #cap velocity if it is too high
        if v_mag > self.max_v:
            self.vx = m.cos(direction)*self.max_v
            self.vy = m.sin(direction)*self.max_v

        change_x = self.x-old_x
        change_y = self.y-old_y
        for child in self.children:
            child.move(change_x, change_y)

    #move entity (with collision check)
    def move(self, ax, ay):
        #compact step calculation method
        steps = m.ceil(max(abs(ax), abs(ay)))
        check_rect = self.rect.copy()
        check_rect.w = self.rect.w*self.cw
        check_rect.h = self.rect.h*self.ch
        cx_offset = self.rect.w*(1-self.cw)
        cy_offset = self.rect.h*(1-self.ch)

        #return from procedure early if no movement
        if ax == 0 and ay == 0:
            return
        
        step_x = ax/steps
        step_y = ay/steps

        nx = self.x
        ny = self.y

        can_move_x = True
        can_move_y = True
        for step in range(steps):
            #break loop if cannot move
            if not can_move_x and not can_move_y:
                break

            #exception variable used instead of just self.collision_exceptions
            exceptions = [self]+self.collision_exceptions

            if self.collision_dict["structures_travel"]:
                horizontal_collision_dict = self.collision_dict.copy()
                horizontal_collision_dict["structures_travel"] = False
            else:
                horizontal_collision_dict = self.collision_dict
                
            if can_move_x:
                check_rect.topleft = (nx+step_x+cx_offset, ny+cy_offset)
                colliding = check_collision(check_rect, self.collision_mask, horizontal_collision_dict, exceptions)
                
                can_move_x = not colliding
                if can_move_y and not can_move_x:
                    self.collide(colliding)
                    
            if can_move_y:
                check_rect.topleft = (nx+cx_offset, ny+step_y+cy_offset)
                colliding = check_collision(check_rect, self.collision_mask, self.collision_dict, exceptions)
                
                can_move_y = not colliding
                if can_move_x and not can_move_y:
                    self.collide(colliding)
                
            if can_move_x:
                nx += step_x
            if can_move_y:
                ny += step_y

        self.x = nx
        self.y = ny

        if not can_move_x:
            self.vx = 0
        if not can_move_y:
            self.vy = 0

        self.update_rect()

        return nx-self.x, ny-self.y, can_move_x, can_move_y

    def draw(self, camera):
        if self.surface:
            camera.draw_transformed_surface(self.surface, self.rect)

    def delete(self):
        entities.remove(self)

    def collide(self, colliding_object):
        pass

class Icon():
    def __init__(self, rect, graphics, visible, timer=None, vx=0, vy=0, tag=None):
        self.rect = rect
        self.x = self.rect.x
        self.y = self.rect.y
        self.graphics = graphics
        self.visible = visible
        self.timer = timer
        self.vx = vx
        self.vy = vy

        self.tag=tag

        self.surface = get_surface(self.graphics)
        
        icons.append(self)

    def update(self):

        self.x += self.vx
        self.y += self.vy
        
        self.rect.x = self.x
        self.rect.y = self.y
        
        if self.timer != None:
            self.timer -= 1
            if self.timer == 0:
                self.delete()

        self.surface = get_surface(self.graphics)

    def delete(self):
        icons.remove(self)

    def draw(self, camera):
        camera.draw_transformed_surface(self.surface, self.rect)

class Hud_Icon(Icon):
    def __init__(self, rect, graphics, visible, timer=None, vx=0, vy=0, tag=None):
        Icon.__init__(self, rect, graphics, visible, timer=timer, vx=vx, vy=vy, tag=tag)

    def draw(self, camera):
        screen.blit(self.surface, self.rect)

class Text_Icon(Icon):
    def __init__(self, rect, font, colour, text, visible, timer=None, vx=0, vy=0, tag=None):
        graphics = font.render(text, False, colour)
        self.surface = get_surface(graphics)
        rect.w, rect.h = font.size(text)
        Icon.__init__(self, rect, graphics, visible, timer=timer, vx=vx, vy=vy, tag=tag)

class Hud_Text_Icon(Hud_Icon):
    def __init__(self, rect, font, colour, text, visible, timer=None, vx=0, vy=0, tag=None):
        graphics = font.render(text, False, colour)
        self.surface = get_surface(graphics)
        rect.w, rect.h = font.size(text)
        Hud_Icon.__init__(self, rect, graphics, visible, timer=timer, vx=vx, vy=vy, tag=tag)

def get_cost(structure_template, height):
    cost = structure_template.cost*( 1 + (height * DEPTH_COST_MULTIPLIER))
    return cost

def get_can_build_structure(structure_template, tx, ty):
    sx = tx
    sy = ty
    ex = sx+structure_template.tw
    ey = sy+structure_template.th

    cost = get_cost(structure_template, ty)
    if money < cost:
        return False

    if not free_build:
        next_to_existing_structure = False
        rect = p.Rect(tx*TW, ty*TH, structure_template.tw*TW, structure_template.th*TH).inflate(4,4)
        for structure in structures:
            if structure.rect.colliderect(rect):
                next_to_existing_structure = True

        if not next_to_existing_structure:
            return False

    rect = p.Rect(sx*TW, sy*TH, structure_template.tw*TW, structure_template.th*TH)
    if not(sx >= 0 and sy >= 0 and ex <= level.t_width and ey <= level.t_height):
        return False

    for x in range(sx,ex):
        for y in range(sy,ey):
            if level.tiles[x][y].name == "empty":
                return False
    
    for structure in structures:
        if structure.rect.colliderect(rect):
            return False

    return True

def get_powered(tx, ty, tile=False):
    powered = False
    for structure in structures:
        if type(structure) == Generator:
            tcx = structure.rect.centerx/TW
            tcy = structure.rect.centery/TH
            if tile:
                dist = get_distance(tx+0.5, ty+0.5, tcx, tcy)
            else:
                dist = get_distance(tx, ty, tcx, tcy)
                
            if dist <= structure.power_range:
                powered = True
                break
    return powered

def get_ventilated(tx, ty, tile=False):
    ventilated = False
    for structure in structures:
        if type(structure) == Ventilator and structure.powered:
            tcx = structure.rect.centerx/TW
            tcy = structure.rect.centery/TH
            if tile:
                dist = get_distance(tx+0.5, ty+0.5, tcx, tcy)
            else:
                dist = get_distance(tx, ty, tcx, tcy)
                
            if dist <= structure.ventilation_range:
                ventilated = True
                break
    return ventilated

def get_money(amount, ox, oy):
    global money

    can_play_sound = True
    for icon in icons:
        if icon.tag == "money":
            can_play_sound = False

    if can_play_sound:
        play_sound("gain_money")
    
    if money+amount > MAX_MONEY:
        amount = MAX_MONEY-money
    
    icon_x = money_icon.rect.right+ox
    icon_y = money_icon.rect.bottom+oy
    rect = p.Rect(icon_x, icon_y, 30, 30)
    Hud_Text_Icon(rect, money_font, YELLOW, "+"+str(round(amount,1)), True, timer=30, vx=1, tag="money")
    money += amount

def lose_money(amount, ox, oy):
    global money

    can_play_sound = True
    for icon in icons:
        if icon.tag == "money":
            can_play_sound = False

    if can_play_sound:
        play_sound("lose_money")
    
    icon_x = money_icon.rect.right+ox
    icon_y = money_icon.rect.bottom+oy
    rect = p.Rect(icon_x, icon_y, 30, 30)
    Hud_Text_Icon(rect, money_font, RED, str(round(-amount,1)), True, timer=30, vx=1, tag="money")
    money -= amount
                
class Structure(Entity):
    def __init__(self, name, tile_rect, health, cost, graphics):
        self.name = name
        rect = p.Rect(tile_rect.x*TW, tile_rect.y*TH, tile_rect.w*TW, tile_rect.h*TH)
        self.max_health = health
        self.health = self.max_health
        self.cost = cost
        Entity.__init__(self, rect, collision_dict={"levels":False, "structures":False, "structures_travel":False, "creatures":False, "player":False, "border":False})
        self.graphics = graphics
        
        self.saved_repair = 0

        removed_tiles = []
        
        sx = tile_rect.x
        sy = tile_rect.y
        ex = sx+tile_rect.w
        ey = sy+tile_rect.h
        for x in range(sx, ex):
            for y in range(sy, ey):
                tile = level.tiles[x][y]
                removed_tiles.append(tile)
                level.tiles[x][y] = Tile(level, x, y, "empty")

        money_x = 0
        money_y = 0
        for tile in removed_tiles:
            value = 0
            if tile.name == "gold":
                value = 200
            elif tile.name == "diamonds":
                value = 300
            elif tile.name == "fossils":
                value = 400

            if value != 0:
                get_money(value, money_x, money_y)
                
                money_y += 30


        unpowered_icon_rect = p.Rect(0,0,TW,TH)
        unpowered_icon_rect.midbottom = self.rect.midtop
        unpowered_icon_rect.x -= (TW/2)
        unpowered_icon_rect.y -= (TH/2)
        self.unpowered_icon = Icon(unpowered_icon_rect, icons_spritesheet.sprites[3][0], visible=False)

        unventilated_icon_rect = p.Rect(0,0,TW,TH)
        unventilated_icon_rect.midbottom = self.rect.midtop
        unventilated_icon_rect.x += (TW/2)
        unventilated_icon_rect.y -= (TH/2)
        self.unventilated_icon = Icon(unventilated_icon_rect, icons_spritesheet.sprites[4][0], visible=False)

        self.powered = False
        self.ventilated = False
        structures.append(self)

        self.assigned_workers = []
        
        self.set_connections()

    def change_health(self, amount):
        self.health += amount
            
        if self.health > self.max_health:
            self.health = self.max_health
        elif self.health <= 0:
            self.delete()

        if amount != 0:
            if amount > 0:
                colour = GREEN
                amount_text = "+"+str(amount)
            else:
                colour = RED
                amount_text = str(amount)

            rect = p.Rect(0,0,TW/2,TH/2)
            rect.midbottom = self.rect.midtop
            rect.y -= 10

            Text_Icon(rect, icon_font, colour, amount_text, True, timer=MAX_TICK_RATE/2, vy=-1)

    def set_connections(self, triggered=False):
        self.connections = []
        
        check_rect = p.Rect(0,0,5,5)
        check_rect.bottomright = self.rect.bottomleft
        for structure in structures:
            if structure != self and structure.rect.colliderect(check_rect):
                self.connections.append( ("left",structure) )
                break

        check_rect.bottomleft = self.rect.bottomright
        for structure in structures:
            if structure != self and structure.rect.colliderect(check_rect):
                self.connections.append( ("right",structure) )
                break

        check_rect.midbottom = self.rect.midtop
        for structure in structures:
            if structure != self and structure.rect.colliderect(check_rect):
                self.connections.append( ("up",structure) )
                break

        check_rect.midtop = self.rect.midbottom
        for structure in structures:
            if structure != self and structure.rect.colliderect(check_rect):
                self.connections.append( ("down",structure) )
                break

        if not triggered:
            for direction,structure in self.connections:
                structure.set_connections(triggered=True)
                
    def draw_connections(self, camera):
        for connection in self.connections:
            direction = connection[0]
            rect = p.Rect(0,0,20,20)
            if direction == "up":
                rect.center = self.rect.midtop
            elif direction == "down":
                rect.center = self.rect.midbottom
            elif direction == "left":
                rect.bottomright = self.rect.bottomleft
            elif direction == "right":
                rect.bottomleft = self.rect.bottomright

            camera.draw_transformed_rect(RED, rect)

            
    def get_powered(self):
        ctx = self.rect.centerx/TW
        cty = self.rect.centery/TH
        powered = get_powered(ctx, cty)
        return powered

    def get_ventilated(self):
        ctx = self.rect.centerx/TW
        cty = self.rect.centery/TH
        ventilated = get_ventilated(ctx, cty)
        return ventilated

    def update(self):
        Entity.update(self)
        if type(self.graphics) == Animation:
            self.graphics.update()
        self.surface = get_surface(self.graphics)
        
        self.powered = self.get_powered()
        self.ventilated = self.get_ventilated()
        
        self.unpowered_icon.visible = not self.powered
        self.unventilated_icon.visible = not self.ventilated

        self.repair_rate = 0
        if self.health < self.max_health:
            for worker in self.assigned_workers:
                self.saved_repair += worker.productivity*0.005
            while self.saved_repair >= 1:
                self.saved_repair -= 1
                self.change_health(1)

    def delete(self):
        Entity.delete(self)
        structures.remove(self)
        for direction,structure in self.connections:
            structure.set_connections(triggered=True)

        for worker in workers:
            if worker.path:
                for structure in worker.path:
                    if structure == self:
                        worker.set_path(worker.target)

        sx = int(self.rect.left/TW)
        sy = int(self.rect.top/TH)
        ex = int(self.rect.right/TW)
        ey = int(self.rect.bottom/TW)
        for x in range(sx,ex):
            for y in range(sy,ey):
                new_tile = Tile(level, x, y, "dirt")
                level.tiles[x][y] = new_tile

        self.unpowered_icon.delete()
        self.unventilated_icon.delete()
        play_sound("destroy")

    def draw_status(self, x, y, font=observe_font):
        text_height = font.size("A")[1]
        name_text = font.render(self.name, False, WHITE)
        screen.blit(name_text, (x,y) )
        
        y += text_height
        health_fraction = self.health/self.max_health
        if health_fraction == 1:
            colour = CYAN
        elif health_fraction >= 0.7:
            colour = GREEN
        elif health_fraction >= 0.3:
            colour = YELLOW
        else:
            colour = RED
        health_string = "Health: "+str(round(self.health,1))+"/"+str(self.max_health)
        health_text = font.render(health_string, False, colour)
        screen.blit(health_text, (x,y))

class Corridor(Structure):
    def __init__(self, tile_rect, cost):
        graphics = load_surface("corridor.png")
        Structure.__init__(self, "corridor", tile_rect, 25, cost, graphics)

    def update(self):
        Structure.update(self)
        self.unpowered_icon.visible = False
        
class Vacuum_Tube(Structure):
    def __init__(self, tile_rect, cost):
        graphics = load_surface("vacuum_tube.png")
        Structure.__init__(self, "vacuum tube", tile_rect, 25, cost, graphics)

class Ventilator(Structure):
    def __init__(self, tile_rect, cost):
        graphics = fans_spritesheet.generate_animation(0, MAX_TICK_RATE/4)
        Structure.__init__(self, "ventilator", tile_rect, 25, cost, graphics)

        self.base_ventilation_range = 5
        self.set_ventilation_range()

    def update(self):
        Structure.update(self)
        self.set_ventilation_range()

    def set_ventilation_range(self):
        added_range = 0
        for worker in self.assigned_workers:
            added_range += worker.productivity*0.4
        self.ventilation_range = self.base_ventilation_range+added_range

    def draw_range(self, camera):
        range_rect = p.Rect(self.rect.centerx, self.rect.centery, 1, 1).inflate(self.ventilation_range*((TW+TH)/2), self.ventilation_range*((TW+TH)/2))
        camera.draw_transformed_ellipse(GREEN, range_rect, 4)

class Generator(Structure):
    def __init__(self, tile_rect, cost):
        graphics = load_surface("generator.png")
        Structure.__init__(self, "generator", tile_rect, 50, cost, graphics)

        self.base_power_range = 7
        self.set_power_range()

    def update(self):
        Structure.update(self)
        self.set_power_range()

    def set_power_range(self):
        added_range = 0
        for worker in self.assigned_workers:
            added_range += worker.productivity*0.6
        self.power_range = self.base_power_range+added_range

    def draw_range(self, camera):
        range_rect = p.Rect(self.rect.centerx, self.rect.centery, 1, 1).inflate(self.power_range*((TW+TH)/2), self.power_range*((TW+TH)/2))
        camera.draw_transformed_ellipse(BLUE, range_rect, 4)

class Mine(Structure):
    def __init__(self, tile_rect, cost):
        graphics = load_surface("mine.png")
        Structure.__init__(self, "mine", tile_rect, 25, cost, graphics)

        self.max_production_timer = MAX_TICK_RATE*5
        self.production_timer = self.max_production_timer

        self.base_production_rate = 1
        self.set_production_rate()

    def update(self):
        Structure.update(self)
        self.set_production_rate()
        if self.powered and self.ventilated:
            self.production_timer -= self.production_rate
            if self.production_timer <= 0:
                self.production_timer = self.max_production_timer
                self.gain(30)

    def set_production_rate(self):
        added_rate = 0
        for worker in self.assigned_workers:
            added_rate += worker.productivity*0.5
        self.production_rate = self.base_production_rate+added_rate

    def gain(self, amount):
        global money
        money += amount
        rect = p.Rect(0,0,TW/2,TH/2)
        rect.midbottom = self.rect.midtop
        rect.y -= 10
            
        Text_Icon(rect, icon_font, GREEN, "+$"+str(amount), True, timer=MAX_TICK_RATE*0.75, vy=-0.75)
        
        
class Farm(Structure):
    def __init__(self, tile_rect, cost):
        graphics = load_surface("farm.png")
        Structure.__init__(self, "generator", tile_rect, 20, cost, graphics)

        self.max_production_timer = MAX_TICK_RATE*5
        self.production_timer = self.max_production_timer

        self.base_production_rate = 1
        self.set_production_rate()

        self.max_produce = 5
        self.produce = 0

    def update(self):
        Structure.update(self)
        self.set_production_rate()
        if self.powered and self.ventilated:
            if self.produce < self.max_produce:
                self.production_timer -= self.production_rate
                if self.production_timer <= 0:
                    self.production_timer = self.max_production_timer
                    self.gain(1)

    def set_production_rate(self):
        added_rate = 0
        for worker in self.assigned_workers:
            added_rate += worker.productivity*0.25
        self.production_rate = self.base_production_rate+added_rate

    def gain(self, amount):
        self.produce += amount
        
        rect = p.Rect(0,0,TW/2,TH/2)
        rect.midbottom = self.rect.midtop
        rect.y -= 10
            
        Text_Icon(rect, icon_font, GREEN, "+"+str(amount)+" food", True, timer=MAX_TICK_RATE*0.75, vy=-0.75)

    def use(self, amount):
        self.produce -= amount
        
        rect = p.Rect(0,0,TW/2,TH/2)
        rect.midbottom = self.rect.midtop
        rect.y -= 10
            
        Text_Icon(rect, icon_font, YELLOW, str(-amount)+" food", True, timer=MAX_TICK_RATE*0.75, vy=-0.75)        

class Housing(Structure):
    def __init__(self, tile_rect, cost):
        graphics = load_surface("housing.png")
        Structure.__init__(self, "housing", tile_rect, 60, cost, graphics)
        self.max_spawn_timer = MAX_TICK_RATE*15
        self.spawn_timer = self.max_spawn_timer
        
        self.attempt_spawn_worker()

    def update(self):
        Structure.update(self)
        self.spawn_timer -= 1
        if self.spawn_timer == 0:
            self.spawn_timer = self.max_spawn_timer
            self.attempt_spawn_worker()

    def attempt_spawn_worker(self):
        max_pop = get_max_population()
        if len(workers) < max_pop:
            tx = (self.rect.x+r.randint(0,(1.6*TW)))/TW
            ty = int(self.rect.y/TH)
            Worker(tx, ty)
            
        
class Structure_Template():
    def __init__(self, structure_class, cost, tw, th):
        self.structure_class = structure_class
        self.tw = tw
        self.th = th
        self.cost = cost

    def attempt_generate(self, tx, ty):
        tile_rect = p.Rect(tx, ty, self.tw, self.th)
        if get_can_build_structure(self, tx, ty):
            cost = get_cost(self, ty)
            lose_money(cost,0,0)
            self.generate(tx, ty)

    def generate(self, tx, ty):
        tile_rect = p.Rect(tx, ty, self.tw, self.th)
        self.structure_class(tile_rect, get_cost(self, ty))

class Creature(Entity):
    def __init__(self, name, rect, animation_system, max_health, speed, cw=1, ch=1):
        Entity.__init__(self, rect, solid=True, collision_dict={"levels":True, "structures":False, "structures_travel":True, "creatures":False, "player":False, "border":False}, cw=cw, ch=ch)
        self.name = name
        
        self.max_health = max_health
        self.health = self.max_health
        self.speed = speed

        self.max_invincibility_timer = int(MAX_TICK_RATE/2)
        self.invincibility_timer = 0

        #the current action of a Creature will determine it's logic and animations
        self.current_action = "static"
        self.animation_system = animation_system

        creatures.append(self)

    def change_health(self, amount):
        self.health += amount

        if amount < 0:
            self.invincibility_timer = self.max_invincibility_timer
            
        if self.health > self.max_health:
            self.health = self.max_health
        elif self.health <= 0:
            self.delete()

    def delete(self):
        Entity.delete(self)
        creatures.remove(self)
    
    def set_animation(self):
        self.animation_system.set_animation(self.current_action)
        self.surface = self.animation_system.get_current_frame()

    def update(self):
        Entity.update(self)
        self.set_animation()
        if self.invincibility_timer > 0:
            self.invincibility_timer -= 1

    def draw(self, camera):
        Entity.draw(self, camera)

class Worker(Creature):
    def __init__(self, tx, ty):
        rect = p.Rect(tx*TW, ty*TH, TW*0.95*(24/52), TH*0.95)

        self.gender = r.choice(["male","female"])
        if self.gender == "male":
            f_name = r.choice(["James", "John", "Robert", "Michael", "William", "David", "Richard", "Charles", "Charlie", "Joseph", "Thomas", "Christopher", "Sam"])
        elif self.gender == "female":
            f_name = r.choice(["Mary", "Patricia", "Linda", "Barbara", "Elizabeth", "Jennifer", "Maria", "Susan", "Margarent", "Dorothy", "Lisa", "Elinor"])
        l_name = r.choice(["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson", "Shepherd"])
        
        name = f_name+" "+l_name
        
        if self.gender == "male":
            spritesheet = worker_male_spritesheet
        elif self.gender == "female":
            spritesheet = worker_female_spritesheet
            
        anim_system = Animation_System(spritesheet, {"static":0,
            "up":1,
            "down":2,
            "left":3,
            "right":4,
            "upleft":5,
            "upright":6,
            "downleft":7,
            "downright":8},
            "static", MAX_TICK_RATE/2)

        health = 20+r.randint(-5,5)
        speed = 2+(r.randint(-1,1)*0.5)+4
        hunger_time = 40
        self.age = r.randint(20,45)
        self.consumption = (1/(MAX_TICK_RATE*hunger_time))+(r.randint(-1,1)*0.25/(MAX_TICK_RATE*hunger_time))
        self.saturation = 1
        self.productivity = 1+(r.randint(-1,1)*0.25)

        self.max_action_check_timer = (2*MAX_TICK_RATE)
        self.action_check_timer = self.max_action_check_timer

        self.target = None
        self.subtarget = None
        self.path = []
        
        Creature.__init__(self, name, rect, anim_system, health, speed)
        self.vx_keep = 0.5
        self.vy_keep = 0.5

        self.assigned_structure = None
        self.getting_food = False
        self.seeking_shelter = False

        workers.append(self)

    def play_selected_sound(self):
        sound_name = r.choice(["sir", "yes"])
        play_sound(sound_name)

    def play_assigned_sound(self):
        sound_name = r.choice(["rightawaysir", "yessir"])
        play_sound(sound_name)

    def update(self):
        Creature.update(self)
        self.set_action()

        self.update_ai()

        if self.saturation > 0:
            self.saturation -= self.consumption      
        if self.saturation <= 0:
            if self.invincibility_timer == 0:
                self.change_health(-1)

        tx = int(self.x/TW)
        ty = int(self.y/TH)
        if level.tiles[tx][ty].name != "empty":
            if self.invincibility_timer == 0:
                self.change_health(-1)

        for structure in structures:
            if structure.rect.colliderect(self.rect) and not structure.ventilated:
                if self.invincibility_timer == 0:
                    self.change_health(-1)

        if self.assigned_structure:
            if self.assigned_structure.rect.colliderect(self.rect):
                if self not in self.assigned_structure.assigned_workers:
                    self.assigned_structure.assigned_workers.append(self)
            else:
                if self in self.assigned_structure.assigned_workers:
                    self.assigned_structure.assigned_workers.remove(self)

                

    def reach_target(self):
        self.path = []
        if type(self.target) == Farm and self.getting_food:
            if self.target.produce >= 1:
                self.target.use(1)
                self.saturation = 1
                
                self.change_health(2)

                if self.health <= self.max_health/2:
                    self.deal_with_hunger()
                else:
                    self.getting_food = False
                    self.reset_path()
                    
    def reset_path(self):
        self.set_path(self.assigned_structure)
        if not self.path:
            self.assigned_structure = None
        self.target = self.assigned_structure

    def change_health(self, amount):
        Creature.change_health(self, amount)

        if amount != 0:
            if amount > 0:
                colour = GREEN
                amount_text = "+"+str(amount)
            else:
                colour = RED
                amount_text = str(amount)

            rect = p.Rect(0,0,TW/2,TH/2)
            rect.midbottom = self.rect.midtop
            rect.y -= 10

            Text_Icon(rect, icon_font, colour, amount_text, True, timer=MAX_TICK_RATE/2, vy=-1)

    def deal_with_hunger(self):
        if self.saturation < 0.35 or self.health <= self.max_health/2:
            if type(self.target) != Farm:
                farms = []
                for structure in structures:
                    if type(structure) == Farm and structure.produce >= 1:
                        farms.append(structure)

                farms = sorted(farms,key=lambda f: get_distance(self.rect.centerx, self.rect.centery, f.rect.centerx, f.rect.centery))

                self.path = []
                for farm in farms:
                    self.set_path(farm)
                    if self.path:
                        self.getting_food = True
                        break

    def deal_with_shelter(self):
        if not self.getting_food:
            if missile_manager.strike_duration_timer > 0:
                if type(self.target) != Housing:
                    housings = []
                    for structure in structures:
                        if type(structure) == Housing:
                            housings.append(structure)

                    housings = sorted(housings,key=lambda f: get_distance(self.rect.centerx, self.rect.centery, f.rect.centerx, f.rect.centery))

                    self.path = []
                    for housing in housings:
                        self.set_path(housing)
                        if self.path:
                            self.seeking_shelter = True
                            break
                    
            if missile_manager.strike_duration_timer == 0 and self.seeking_shelter:
                self.seeking_shelter = False
                self.reset_path()

    def update_ai(self):
        if self.action_check_timer > 0:
            self.action_check_timer -= 1
        else:
            self.action_check_timer = self.max_action_check_timer
            
            self.deal_with_shelter()
            self.deal_with_hunger()
                        
        new_subtarget_range = 10
        containment_rect = p.Rect(0,0,new_subtarget_range,new_subtarget_range)
        containment_rect.center = self.rect.center

        in_tube = False
        for structure in structures:
            if type(structure) == Vacuum_Tube and structure.rect.colliderect(self.rect):
                in_tube = structure
                break
        
        if self.subtarget in structures:
            reached_subtarget = False
            index = self.path.index(self.subtarget)
            if index+1 == len(self.path):
                reached_subtarget = containment_rect.collidepoint(self.subtarget.rect.center)
            else:
                reached_subtarget = self.rect.contains(self.subtarget.rect) or self.subtarget.rect.contains(containment_rect)
            
                              
            if reached_subtarget:
                
                if index+1 == len(self.path):
                    self.subtarget = None
                    self.reach_target()
                else:
                    self.subtarget = self.path[index+1]

        if self.subtarget in structures:
            if self.rect.centerx < self.subtarget.rect.centerx:
                self.vx = self.speed
            if self.rect.centerx > self.subtarget.rect.centerx:
                self.vx = -self.speed

            if in_tube:
                subtarget_dif = self.subtarget.rect.centery-self.rect.centery
                if subtarget_dif < 0  :
                    self.vy = -min(abs(subtarget_dif),self.speed)
                elif subtarget_dif > 0:
                    self.vy = min(abs(subtarget_dif),self.speed)
                        
        if not in_tube:  
            self.vy = GRAVITY

            

        

    def set_action(self):
        self.current_action = "static"
        diagonal_limit = 1
        if self.vx < 0:
            if self.vy < -diagonal_limit:
                self.current_action = "upleft"
            elif self.vy > diagonal_limit:
                self.current_action = "downleft"
            else:
                self.current_action = "left"

        elif self.vx > 0:
            if self.vy < -diagonal_limit:
                self.current_action = "upright"
            elif self.vy > diagonal_limit:
                self.current_action = "downright"
            else:
                self.current_action = "right"

        elif self.vy < 0:
            self.current_action = "up"
        elif self.vy > 0:
            self.current_action = "down"

    def delete(self):
        global selected_worker
        
        Creature.delete(self)
        workers.remove(self)
        if selected_worker == self:
            selected_worker = None

        play_sound("death")

    def draw_status(self, x, y, font=observe_font):
        text_height = font.size("A")[1]
        name_text = font.render(self.name, False, WHITE)
        screen.blit(name_text, (x,y) )
        
        y += text_height
        health_fraction = self.health/self.max_health
        if health_fraction == 1:
            colour = CYAN
        elif health_fraction >= 0.7:
            colour = GREEN
        elif health_fraction >= 0.3:
            colour = YELLOW
        else:
            colour = RED
        health_string = "Health: "+str(self.health)+"/"+str(self.max_health)
        health_text = font.render(health_string, False, colour)
        screen.blit(health_text, (x,y))

        y += text_height
        info_string = str(self.age)+", "+self.gender
        info_text = font.render(info_string, False, WHITE)
        screen.blit(info_text, (x,y))

        y += text_height
        if not self.assigned_structure:
            assigned_structure_string = "None"
            colour = RED
        else:
            structure_type = type(self.assigned_structure)
            if structure_type == Corridor:
                assigned_structure_string = "Corridor"
            elif structure_type == Housing:
                assigned_structure_string = "Housing"
            elif structure_type == Ventilator:
                assigned_structure_string = "Fan"
            elif structure_type == Generator:
                assigned_structure_string = "Generator"
            elif structure_type == Mine:
                assigned_structure_string = "Mine"
            elif structure_type == Farm:
                assigned_structure_string = "Farm"
            elif structure_type == Vacuum_Tube:
                assigned_structure_string = "Vacuum Tube"
            
            colour = WHITE
            
        assigned_string = "Assigned: "+assigned_structure_string
        assigned_text = font.render(assigned_string, False, colour)
        screen.blit(assigned_text, (x,y))

        y += text_height
        if self.saturation == 1:
            colour = CYAN
        elif self.saturation >= 0.7:
            colour = GREEN
        elif self.saturation >= 0.3:
            colour = YELLOW
        else:
            colour = RED
        hunger_string = "Food: "+str(round(+self.saturation*100))+"%"
        hunger_text = font.render(hunger_string, False, colour)
        screen.blit(hunger_text, (x,y))

    def set_path(self, target):
        self.path = []
        start_node = None
        for structure in structures:
            if structure.rect.colliderect(self.rect):
                start_node = structure
                break

        if start_node:
            self.path = find_path(start_node, target, [], 1)

        if self.path:
            self.target = target
            self.subtarget = self.path[0]
        else:
            self.target = None
            self.subtarget = None

def find_path(start_node, target_node, _path, depth, max_depth=25):
    path = _path.copy()
    path.append(start_node)

    if start_node == target_node:
        return path
    if depth > max_depth:
        return False

    target_node_path = None
    connections = []
    for direction, structure in start_node.connections:
        if type(structure) == Vacuum_Tube or direction == "left" or direction == "right":
            connections.append((direction, structure))

    valid_paths = []
    for direction, structure in connections:
        
        if structure not in path and structure.ventilated:
            target_node_path = find_path(structure, target_node, path, depth+1)
            if target_node_path:
                valid_paths.append(target_node_path)

    
    best_dist = 9999
    best_path = None
    for path in valid_paths:
        if path:
            if len(path) < best_dist:
                best_dist = len(path)
                best_path = path
    return best_path


class Player(Creature):
    def __init__(self, rect, animation_system, health, speed, cw=1, ch=0.5):
        Creature.__init__(self, "player", rect, animation_system, health, speed, cw=cw, ch=ch)

    def update(self):
        Creature.update(self)
        self.set_action()

    def set_action(self):
        self.current_action = "static"
        diagonal_limit = 1
        if self.vx < 0:
            if self.vy < -diagonal_limit:
                self.current_action = "upleft"
            elif self.vy > diagonal_limit:
                self.current_action = "downleft"
            else:
                self.current_action = "left"

        elif self.vx > 0:
            if self.vy < -diagonal_limit:
                self.current_action = "upright"
            elif self.vy > diagonal_limit:
                self.current_action = "downright"
            else:
                self.current_action = "right"

        elif self.vy < 0:
            self.current_action = "up"
        elif self.vy > 0:
            self.current_action = "down"
            

    def draw(self, camera):
        Creature.draw(self, camera)

class Projectile(Entity):
    def __init__(self, rect, vx, vy, graphics, creator, collision_dict={"levels":True, "structures":True, "structures_travel":False, "creatures":False, "player":False, "border":True}):
        Entity.__init__(self, rect, vx=vx, vy=vy, vx_keep=1, vy_keep=1, collision_dict=collision_dict, collision_exceptions=[creator])
        self.graphics = graphics
        projectiles.append(self)
        self.update()
        

    def update(self):
        Entity.update(self)
        self.surface = get_surface(self.graphics)

    def draw(self, camera):
        camera.draw_transformed_surface(self.surface, self.rect)

    def delete(self):
        Entity.delete(self)
        projectiles.remove(self)

    def collide(self, colliding_object):
        Entity.collide(self, colliding_object)
        self.delete()

class Effect(Entity):
    def __init__(self, rect, vx, vy, timer, graphics):
        Entity.__init__(self, rect, vx=vx, vy=vy, collision_dict={"levels":True, "structures":False, "structures_travel":False, "creatures":False, "player":False, "border":True})
        Delete_Event(self, timer)
        self.graphics = graphics
        self.update()

        effects.append(self)

    def update(self):
        Entity.update(self)
        self.surface = get_surface(self.graphics)
        
    def draw(self, camera):
        camera.draw_transformed_surface(self.surface, self.rect)

    def delete(self):
        Entity.delete(self)
        effects.remove(self)

class Explosion():
    def __init__(self, x, y, graphics, radius, timer, damage_timer, damage):
        play_sound("explosion")
        self.x = x
        self.y = y
        self.graphics = graphics
        self.max_radius = radius
        self.radius = 1
        self.max_timer = timer
        self.timer = self.max_timer
        self.damage = damage
        
        self.max_damage_timer = damage_timer
        self.damage_timer = self.max_damage_timer
        
        self.collision_dict={"levels":True, "structures":True, "structures_travel":False, "creatures":True, "player":False, "border":False}

        explosions.append(self)
        self.update()

    def update(self):
        if type(self.graphics) == Animation:
            self.graphics.update()
            
        self.timer -= 1
        self.radius = interpolate_between_values(1,self.max_radius, 1-(self.timer/self.max_timer))

        self.damage_timer -= 1
        if self.damage_timer <= 0:
            self.damage_timer = self.max_damage_timer
            self.damage_objects()

        if self.timer == 0:
            explosions.remove(self)

        self.rect = p.Rect(0,0,self.radius*2,self.radius*2)
        self.rect.center = (self.x,self.y)

        self.surface = get_surface(self.graphics)

    def damage_objects(self):
        colliding_objects = check_collision(self.rect, None, self.collision_dict, [self], full=True)
        for colliding_object in colliding_objects:
            if type(colliding_object) == Tile:
                colliding_object.change_health(-self.damage)
            elif isinstance(colliding_object, Creature):
                colliding_object.change_health(-self.damage)
            elif isinstance(colliding_object, Structure):
                colliding_object.change_health(-self.damage)

    def draw(self, camera):
        camera.draw_transformed_surface(self.surface, self.rect)

class Missile(Projectile):
    def __init__(self, rect, graphics, vy):
        Projectile.__init__(self, rect, 0, vy, graphics, None, collision_dict={"levels":True, "structures":True, "structures_travel":False, "creatures":True, "player":False, "border":True})
        self.played_sound = False;

    def update(self):
        if type(self.graphics) == Animation:
            self.graphics.update()
            
        Projectile.update(self)
        if self.rect.bottom >= sky.rect.top and not self.played_sound:
            play_sound("missile")
            self.played_sound = True

    def collide(self, colliding_object):
        Projectile.collide(self, colliding_object)
        
        Explosion(self.rect.midbottom[0], self.rect.midbottom[1], explosions_spritesheet.generate_animation(0, MAX_TICK_RATE/4), TW*2.5, MAX_TICK_RATE*2, MAX_TICK_RATE/8, 2)

class Missile_Manager():
    def __init__(self, strike_timer, strike_length, strike_number, strike_number_variance, strike_number_increase_rate, strike_number_cap=25):
        self.max_strike_timer = strike_timer
        self.strike_timer = self.max_strike_timer

        self.strike_length = strike_length
        self.strike_duration_timer = 0

        self.strike_number = strike_number
        self.strike_number_variance = strike_number_variance

        self.strike_number_increase_rate = strike_number_increase_rate
        self.strike_number_cap = strike_number_cap

    def update(self):
        if self.strike_duration_timer > 0:
            self.strike_duration_timer -= 1

        else:
            self.strike_timer -= 1
            if self.strike_timer == 0:
                self.strike_timer = self.max_strike_timer
                self.strike_duration_timer = self.strike_length
                fired_missiles = min(self.strike_number+r.randint(-self.strike_number_variance, self.strike_number_variance), self.strike_number_cap)
                play_sound("alert")
                self.fire(fired_missiles)
                self.strike_number += self.strike_number_increase_rate

    def fire(self, amount):
        for missile in range(amount):
            y = (r.randint(-30,0)-12)*TH
            x = r.randint(0,level.width)
            vy = r.randint(3,5)

            rect = p.Rect(0,0,TW,TH*3)
            rect.center = (x,y)
            graphics = missiles_spritesheet.generate_animation(0,MAX_TICK_RATE/4)

            Missile(rect, graphics, vy)

class Camera(Entity):
    def __init__(self, rect):
        Entity.__init__(self, rect, visible=False, collision_dict={"levels":False, "structures":False, "structures_travel":False, "creatures":False, "player":False, "border":False})

        self.update()

    def update(self):
        Entity.update(self)
        self.scale_x = WIDTH/self.rect.width
        self.scale_y = HEIGHT/self.rect.height
        self.screen_x = self.x - ((WIDTH/2)/self.scale_x)
        self.screen_y = self.y - ((HEIGHT/2)/self.scale_y)

    def center_screen(self, point):
        self.x = point[0]
        self.y = point[1]

    def transform_point(self, x, y):
        x = ((x-self.x)*self.scale_x) + (WIDTH/2)
        y = ((y-self.y)*self.scale_y) + (HEIGHT/2)
        
        return x,y

    def reverse_transform_point(self, x, y):
        new_x = x-(WIDTH/2)
        new_y = y-(HEIGHT/2)
        
        new_x /= self.scale_x
        new_y /= self.scale_y
        
        new_x += self.x
        new_y += self.y
        return new_x, new_y
    

    def transform_rect(self, rect):
        x, y = self.transform_point(rect.left, rect.top)
        width = rect.width*self.scale_x
        height = rect.height*self.scale_y

        rect = p.Rect(x, y, width, height)
        return rect

    def draw_transformed_surface(self, surface, rect):
        new_rect = self.transform_rect(rect)
        new_surface = p.transform.scale(surface, (new_rect.w, new_rect.h))
        screen.blit(new_surface, new_rect)

    def draw_transformed_rect(self, colour, rect, border=0):
        rect = self.transform_rect(rect)
        p.draw.rect(screen, colour, rect, border)

    def draw_transformed_ellipse(self, colour, rect, border=0):
        rect = self.transform_rect(rect)
        p.draw.ellipse(screen, colour, rect, border)


#player_spritesheet = Spritesheet("creature_test.png", 32, 32, transparency_pixel=TRANSPARENCY_COLOUR)
#player_anims = Animation_System(player_spritesheet,
#                               {"static":0,
#                               "up":1,
#                               "down":2,
#                               "left":3,
#                               "right":4,
#                                "upleft":5,
#                                "upright":6,
#                                "downleft":7,
#                                "downright":8},
#                               "static", MAX_TICK_RATE)

tile_spritesheet = Spritesheet("tiles.png", 64, 64, transparency_pixel=TRANSPARENCY_COLOUR)
buttons_spritesheet = Spritesheet("buttons.png", 64, 32)
build_options_spritesheet = Spritesheet("build_options.png", 64, 32)
icons_spritesheet = Spritesheet("icons.png", 32, 32, transparency_pixel=TRANSPARENCY_COLOUR)
worker_male_spritesheet = Spritesheet("worker_male.png", 24, 52, transparency_pixel=TRANSPARENCY_COLOUR)
worker_female_spritesheet = Spritesheet("worker_female.png", 24, 52, transparency_pixel=TRANSPARENCY_COLOUR)
missiles_spritesheet = Spritesheet("missiles.png", 29, 82, transparency_pixel=TRANSPARENCY_COLOUR)
explosions_spritesheet = Spritesheet("explosions.png", 64, 64, transparency_pixel=TRANSPARENCY_COLOUR)
fans_spritesheet = Spritesheet("fans.png", 64, 64, transparency_pixel=TRANSPARENCY_COLOUR)

Info_Window_Border(p.Rect(dnmx(0), dnmy(0), dnmx(0.3), dnmy(0.2)))
build_menu = Build_Menu(p.Rect(dnmx(0.05),dnmy(0.02),dnmx(0.9),dnmy(0.10)), load_surface("build_menu_border.png"), dnmx(0.1), dnmy(0.05), dnmx(0.02))

#what if two people walk up to an elavator in quick succession?
    #Mask_Level("test1", level_scale_x=LEVEL_SCALE_X, level_scale_y=LEVEL_SCALE_Y)

menu_slides = Slides(p.Rect(0,0,WIDTH,HEIGHT), ["title.png", "sl_modes.png", "sl_navigation.png", "sl_workers1.png","sl_workers2.png","sl_workers3.png","sl_structures1.png","sl_structures2.png","sl_structures3.png","sl_structures4.png","sl_structures5.png", "sl_strikes.png"], ["start"])
Button("start_button", p.Rect(dnmx(0.35),dnmy(0.7),dnmx(0.3),dnmy(0.2)), buttons_spritesheet.sprites[0][0], buttons_spritesheet.sprites[0][0], ["start"], False)

Decoration(p.Rect(0,0,WIDTH,HEIGHT), load_surface("gameover.png"), ["gameover"])

observe_button = Button("observe_button", p.Rect(dnmx(0),dnmy(0.2),dnmx(0.06),dnmy(0.06)), icons_spritesheet.sprites[2][0], icons_spritesheet.sprites[2][0], ["main"], False)
build_button = Button("build_button", p.Rect(dnmx(0),dnmy(0.2+0.06),dnmx(0.06),dnmy(0.06)), icons_spritesheet.sprites[0][0], icons_spritesheet.sprites[0][0], ["main"], False)
worker_button = Button("worker_button", p.Rect(dnmx(0),dnmy(0.2+0.12),dnmx(0.06),dnmy(0.06)), icons_spritesheet.sprites[1][0], icons_spritesheet.sprites[1][0], ["main"], False)
demolish_button = Button("demolish_button", p.Rect(dnmx(0),dnmy(0.2+0.18),dnmx(0.06),dnmy(0.06)), icons_spritesheet.sprites[7][0], icons_spritesheet.sprites[7][0], ["main"], False)

Button("worker_assign_button", p.Rect(dnmx(0.3),dnmy(0),dnmx(0.12),dnmy(0.05)), buttons_spritesheet.sprites[3][0], buttons_spritesheet.sprites[3][0], ["main"], ["workers"])
#test_decoration = Decoration(p.Rect(10,300,120,80), buttons_spritesheet.sprites[0][0], ["start"])

money_icon = Decoration(p.Rect(dnmx(0), dnmy(0.2+0.24), dnmx(0.05), dnmy(0.05) ), icons_spritesheet.sprites[5][0], ["main"])
money_text_box = Text_Box(p.Rect(dnmx(0.05), dnmy(0.2+0.24), dnmx(0.16), dnmy(0.05) ), HUD_font, "", ["main"])

missile_manager = Missile_Manager(MAX_TICK_RATE*60, MAX_TICK_RATE*12, 8, 3, 2)
            # strike_timer, strike_length, strike_number, strike_number_variance, strike_number_increase_rate
missile_strike_timer_background = Decoration(p.Rect(dnmx(0.83), dnmy(0.3), dnmx(0.17), dnmy(0.08) ), load_surface("missile_timer_background.png"), ["main"])
rect = missile_strike_timer_background.rect.copy()
rect.x += dnmy(0.01)
rect.y += dnmy(0.04)
missile_strike_timer_text_box = Text_Box(rect, timer_font, "", ["main"])

worker_count_icon = Decoration(p.Rect(dnmx(0.95), dnmy(0.4), dnmx(0.05), dnmy(0.05) ), icons_spritesheet.sprites[6][0], ["main"])
work_counter_text_box = Text_Box(p.Rect(dnmx(0.95-0.12), dnmy(0.4), dnmx(0.12), dnmy(0.05) ), timer_font, "", ["main"])

cost_text_box = Text_Box(p.Rect(0,0,60,20), cost_font, "", ["main"], colour=CYAN)


Build_Option("corridor", build_options_spritesheet.sprites[0][0], build_menu)
Build_Option("vacuum tube", build_options_spritesheet.sprites[1][0], build_menu)
Build_Option("ventilator", build_options_spritesheet.sprites[2][0], build_menu)
Build_Option("generator", build_options_spritesheet.sprites[3][0], build_menu)
Build_Option("mine", build_options_spritesheet.sprites[4][0], build_menu)
Build_Option("farm", build_options_spritesheet.sprites[5][0], build_menu)
Build_Option("housing", build_options_spritesheet.sprites[6][0], build_menu)


corridor_template = Structure_Template(Corridor, 50, 1, 1)
vacuum_tube_template = Structure_Template(Vacuum_Tube, 75, 1, 1)
ventilator_template = Structure_Template(Ventilator, 100, 1, 1)
generator_template = Structure_Template(Generator, 200, 3, 1)
mine_template = Structure_Template(Mine, 300, 1, 1)
farm_template = Structure_Template(Farm, 100, 2, 1)
housing_template = Structure_Template(Housing, 200, 2, 1)


#strike_timer, strike_length, strike_number, strike_timer_variance, strike_number_variance

def build_starting_base():
    bx = 2
    by = 4
    generator_template.generate(bx,by)
    housing_template.generate(bx+3,by)
    corridor_template.generate(bx+5,by)
    ventilator_template.generate(bx+4,by-1)
    farm_template.generate(bx+6,by)
    farm_template.generate(bx+8,by)
    farm_template.generate(bx+10,by)
    ventilator_template.generate(bx+8,by-1)
    ventilator_template.generate(bx+11,by-1)
    generator_template.generate(bx+13,by)
    vacuum_tube_template.generate(bx+12,by)
    vacuum_tube_template.generate(bx+12,by+1)
    vacuum_tube_template.generate(bx+12,by+2)
    vacuum_tube_template.generate(bx+12,by+3)
    vacuum_tube_template.generate(bx+12,by+4)
    vacuum_tube_template.generate(bx+12,by+5)
    vacuum_tube_template.generate(bx+12,by+6)
    vacuum_tube_template.generate(bx+12,by+7)
    vacuum_tube_template.generate(bx+12,by+8)
    ventilator_template.generate(bx+4,by+3)
    ventilator_template.generate(bx+8,by+3)
    ventilator_template.generate(bx+11,by+3)
    generator_template.generate(bx+13,by+4)
    corridor_template.generate(bx+11,by+8)
    ventilator_template.generate(bx+13,by+6)
    corridor_template.generate(bx+11,by+4)
    corridor_template.generate(bx+10,by+4)
    corridor_template.generate(bx+9,by+4)
    corridor_template.generate(bx+8,by+4)
    corridor_template.generate(bx+7,by+4)
    corridor_template.generate(bx+6,by+4)
    mine_template.generate(bx+5,by+4)
    mine_template.generate(bx+4,by+4)
    mine_template.generate(bx+3,by+4)
    generator_template.generate(bx,by+4)
    vacuum_tube_template.generate(bx-1,by)
    vacuum_tube_template.generate(bx-1,by+1)
    vacuum_tube_template.generate(bx-1,by+2)
    vacuum_tube_template.generate(bx-1,by+3)
    vacuum_tube_template.generate(bx-1,by+4)
    ventilator_template.generate(bx-2,by+2)
    
    

def reset():
    global camera, level, money, sky, free_build

    missile_manager.strike_timer = missile_manager.max_strike_timer
    missile_manager.strike_duration = 0
    
    entities.clear()
    creatures.clear()
    animations.clear()
    animation_systems.clear()
    projectiles.clear()
    effects.clear()
    events.clear()
    interface_components = []
    buttons = []
    overlays.clear()

    structures.clear()
    workers.clear()
    icons.clear()
    explosions.clear()

    active_levels.clear()

    
    camera = Camera(p.Rect(5,10,TW*15,TH*15))
    level = Tile_Level(20, 200, TW, TH)
    camera.center_screen((level.rect.centerx, 0))

    sky_rect = p.Rect(0,0,level.width,TH*8)
    sky_rect.bottomleft = (0,0)
    sky = Icon(sky_rect, load_surface("sky.png"), True)

    money = 0
    free_build = True
    build_starting_base()
    free_build = False
    for icon in icons:
        if icon.tag == "money":
            icon.delete()
    
    money = 3000

def handle_input():
    global current_state, current_substate
    global keys, mx, my, ml, mm, mr
    global selected_worker
    
    for event in p.event.get():
        if event.type == p.QUIT:
            p.display.quit()
            quit()
        if current_state == "main":
            if event.type == p.MOUSEBUTTONDOWN:
                highlighting_button = False
                for button in buttons:
                    if button.check_highlighted():
                        highlighting_button = True

                if not highlighting_button:
                    if event.button == 1 and current_substate == "build" and selected_build_structure and selected_tile:
                        selected_build_structure.attempt_generate(selected_tile.tx, selected_tile.ty)
                    if event.button == 1 and current_substate == "demolish" and selected_structure:
                        cost = (selected_structure.cost*0.2)
                        lose_money(cost, 0, 0)
                        selected_structure.delete()
                        
                    if current_substate == "workers":
                        old_worker = selected_worker
                        for worker in workers:
                            t_mx, t_my = camera.reverse_transform_point(mx, my)
                            if worker.rect.collidepoint((t_mx, t_my)):
                                selected_worker = worker

                        if selected_worker != old_worker:
                            selected_worker.play_selected_sound()
                        
                                
                    if current_substate == "worker_assign":
                        if selected_structure:
                            selected_worker.set_path(selected_structure)
                            if selected_worker.path:
                                play_sound("success")
                                selected_worker.assigned_structure = selected_structure
                                play_sound("footstep")
                                selected_worker.play_assigned_sound()
                                current_substate = "workers"
                            else:
                                play_sound("denied")
            elif event.type == p.KEYDOWN:
                if event.key == p.K_1 or event.key == p.K_KP1:
                    observe_button.press()
                elif event.key == p.K_2 or event.key == p.K_KP2:
                    build_button.press()
                elif event.key == p.K_3 or event.key == p.K_KP3:
                    worker_button.press()
                elif event.key == p.K_4 or event.key == p.K_KP4:
                    demolish_button.press()
                            
        elif current_state == "start":
            if event.type == p.MOUSEBUTTONDOWN:
                highlighting_button = False
                for button in buttons:
                    if button.check_highlighted():
                        highlighting_button = True

                if not highlighting_button:
                    if event.button == 1:
                        menu_slides.progress(1)
                    if event.button == 3:
                        menu_slides.progress(-1)
                

        elif current_state == "gameover":
            if event.type == p.MOUSEBUTTONDOWN:
                current_state = "start"
                set_music("music_menu")

    keys = p.key.get_pressed()

    if current_state == "main":
        if keys[p.K_UP]:
            camera.y -= 7
        if keys[p.K_DOWN]:
            camera.y += 7
        if keys[p.K_LEFT]:
            camera.x -= 7
        if keys[p.K_RIGHT]:
            camera.x += 7


    mx, my = p.mouse.get_pos()
    ml, mm, mr = p.mouse.get_pressed()

def update():
    #level.set_active_chunks(player.rect.center)
    global current_state
    global selected_tile, selected_structure
    
    if current_state == "main":
        for event in events:
            event.update()
        for entity in entities:
            entity.update()
        for explosion in explosions:
            explosion.update()
        missile_manager.update()
            
        for icon in icons:
            icon.update()
            
        money_text_box.text = str(int(money))
        work_counter_text_box.text = "x"+str(len(workers))

        if missile_manager.strike_duration_timer:
            timer = "--:-"
        else:
            seconds_until_strike = (missile_manager.strike_timer // MAX_TICK_RATE)
            second_fraction_until_strike = round((missile_manager.strike_timer % MAX_TICK_RATE)/MAX_TICK_RATE*60/10)  
            timer = str(seconds_until_strike)+":"+str(second_fraction_until_strike)

        if missile_manager.strike_timer < 10:
            missile_strike_timer_text_box.text_colour = RED
        else:
            missile_strike_timer_text_box.text_colour = BLACK
            
        missile_strike_timer_text_box.text = str(timer)

        t_mx, t_my = camera.reverse_transform_point(mx, my)
        selected_structure = None
        for structure in structures:
            if structure.rect.collidepoint((t_mx, t_my)):
                selected_structure = structure
        
        t_mx = int(t_mx/TW)
        t_my = int(t_my/TH)
        if t_mx >= 0 and t_my >= 0 and t_mx < level.t_width and t_my < level.t_height:
            selected_tile = level.tiles[t_mx][t_my]
        else:
            selected_tile = None

        n_mx = nmx(mx)
        n_my = nmy(my)

        if mr:
            dx = mx-(WIDTH/2)
            dy = my-(HEIGHT/2)
            mag = ((dx**2)+(dy**2))**0.5 / (((WIDTH/2)**2)+((HEIGHT/2)**2))**0.5 * 20
            angle = get_angle(0, 0, dx, dy)
            cx = m.cos(angle)*mag
            cy = m.sin(angle)*mag
            camera.x += cx
            camera.y += cy
            
            
                
        camera_screen_rect = p.Rect(camera.screen_x, camera.screen_y, camera.rect.w, camera.rect.h)

        if camera_screen_rect.right > level.width:
           camera_screen_rect.right = level.width
           
        if camera_screen_rect.left < 0:
           camera_screen_rect.left = 0

        if camera_screen_rect.top < sky.rect.top:
            camera_screen_rect.top = sky.rect.top

        if camera_screen_rect.bottom > level.rect.bottom:
            camera_screen_rect.bottom = level.rect.bottom
            
        dx = camera_screen_rect.x-int(camera.screen_x)
        dy = camera_screen_rect.y-int(camera.screen_y)
        camera.x += dx
        camera.y += dy

        if len(workers) == 0:
            current_state = "gameover"
            p.mixer.music.stop()
            play_sound("lose")
                
    elif current_state == "start":
        pass

        
            
    for interface_component in interface_components:
        interface_component.update()

    if current_substate == "build" and selected_tile and selected_build_structure:
        cost_text_box.colour = RED
        cost_text_box.text = str(round(get_cost(selected_build_structure, selected_tile.ty)))
        cost_text_box.rect.midbottom = (mx,my)
    elif current_substate == "demolish" and selected_structure:
        cost_text_box.colour = RED
        cost_text_box.text = str(round(get_cost(selected_structure, selected_tile.ty))*0.2)
        cost_text_box.rect.midbottom = (mx,my)
    else:
        cost_text_box.active = False
    

def draw():
    if current_state == "main":
        sky.draw(camera)
        
        for level in active_levels:
            level.draw(camera)

        for structure in structures:
            structure.draw(camera)
            
        for creature in creatures:
            creature.draw(camera)

        for projectile in projectiles:
            projectile.draw(camera)
    
        for explosion in explosions:
            explosion.draw(camera)

        if current_substate == "observe":
            for structure in structures:
                if type(structure) == Generator or type(structure) == Ventilator:
                    structure.draw_range(camera)
            
        for icon in icons:
            if icon.visible and icon != sky:
                icon.draw(camera)

        if (current_substate == "build" or current_substate == "observe"):
            if selected_structure:
                camera.draw_transformed_rect(RED, selected_structure.rect, 2)
            elif selected_tile:
                camera.draw_transformed_rect(RED, selected_tile.rect, 2)

        if current_substate == "demolish":
            if selected_structure:
                camera.draw_transformed_rect(RED, selected_structure.rect, 2)
            
        if current_substate == "build" and selected_tile and selected_build_structure:
            build_tile_rect = p.Rect(selected_tile.tx, selected_tile.ty, selected_build_structure.tw, selected_build_structure.th)
            if get_can_build_structure(selected_build_structure, selected_tile.tx, selected_tile.ty):
                build_highlight_colour = GREEN
            else:
                build_highlight_colour = RED
            build_rect = p.Rect(build_tile_rect.x*TW, build_tile_rect.y*TH, build_tile_rect.w*TW, build_tile_rect.h*TH)
            camera.draw_transformed_rect(build_highlight_colour, build_rect, 4)

        if current_substate == "workers" and selected_worker:
            camera.draw_transformed_rect(RED, selected_worker.rect, 2)

        if current_substate == "worker_assign":
            if selected_structure:
                camera.draw_transformed_rect(RED, selected_structure.rect, 2)
    
        for overlay in overlays:
            overlay.draw()
        
    for animation_system in animation_systems:
        animation_system.update()
        
    for interface_component in interface_components:
        if interface_component.active:
            interface_component.draw()

    if current_substate == "observe":
        if selected_structure:
            selected_structure.draw_status(dnmx(0.01), dnmy(0.01))
        elif selected_tile:
            selected_tile.draw_status(dnmx(0.01), dnmy(0.01))
            
    elif current_substate == "workers":
        if selected_worker:
            selected_worker.draw_status(dnmx(0.01), dnmy(0.01))

    elif current_substate == "worker_assign":
        if selected_structure:
            selected_structure.draw_status(dnmx(0.01), dnmy(0.01))

set_music("music_menu")  
RUNNING = True
while RUNNING:
    screen.fill(WHITE)
    handle_input()
    update()
    draw()
    p.display.flip()

    clock.tick(MAX_TICK_RATE)
