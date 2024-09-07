bl_info = {
    "name": "Piano Animation from Melody",
    "blender": (4, 0, 0),
    "category": "Animation",
}

import bpy
import os
import mido

class PianoAnimationOperator(bpy.types.Operator):
    bl_idname = "object.piano_animation_operator"
    bl_label = "Create Piano Animation"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        notes = parse_midi(self.filepath)
        create_piano_keys_and_base(context)
        animate_keys(notes)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def menu_func(self, context):
    self.layout.operator(PianoAnimationOperator.bl_idname)

def register():
    bpy.utils.register_class(PianoAnimationOperator)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(PianoAnimationOperator)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

if __name__ == "__main__":
    register()

def parse_midi(file_path):
    midi = mido.MidiFile(file_path)
    notes = []
    note_times = {}
    current_time = 0

    for msg in midi:
        current_time += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            note = msg.note
            if note not in note_times:
                note_times[note] = []
            note_times[note].append({'start': current_time})
        elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
            note = msg.note
            if note in note_times and note_times[note]:
                note_info = note_times[note].pop(0)
                note_info['end'] = current_time
                notes.append((note, note_info['start'], note_info['end']))

    return notes

def convert_time_to_frame(time, fps=24):
    return int(time * fps)

def create_material(name, color):
    material = bpy.data.materials.new(name=name)
    material.diffuse_color = color
    return material

def create_piano_keys_and_base(context):
    # Create white material
    white_material = create_material("WhiteMaterial", (1, 1, 1, 1))
    # Create black material
    black_material = create_material("BlackMaterial", (0, 0, 0, 1))
    # Create base material
    base_material = create_material("BaseMaterial", (0.25, 0.1, 0.05, 1)) 
    
    # Create base
    bpy.ops.mesh.primitive_cube_add(size=1, location=(26, 0, -1))
    base_object = bpy.context.object
    base_object.scale = (52, 5, 1)
    base_object.name = "PianoBase"
    base_object.data.materials.append(base_material)

    # Create white keys
    # (21 = A)
    white_key_midi_numbers = [21, 23, 24, 26, 28, 29, 31, 33, 35, 36, 38, 40, 41, 43, 45, 47, 48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84, 86, 88, 89, 91, 93, 95, 96, 98, 100, 101, 103, 105, 107, 108]
    for i in range(52):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(i + 0.5, 0, 0))
        key_object = bpy.context.object
        key_object.name = f"WhiteKey_{white_key_midi_numbers[i]}"
        key_object.scale = (1, 4.5, 1) 
        key_object.data.materials.append(white_material)

    #Create black keys    
    black_key_midi_numbers = [22, 25, 27, 30, 32, 34, 37, 39, 42, 44, 46, 49, 51, 54, 56, 58, 61, 63, 66, 68, 70, 73, 75, 78, 80, 82, 85, 87, 90, 92, 94, 97, 99, 102, 104, 106]
    black_key_positions = [1, 3, 4, 6, 7]
    midi_index = 0 
    for i in range(8):  # Repeat for 7 octaves
        for pos in black_key_positions:
            if i == 7 and pos > 1:  # Last octave only has A#
                break
            else:
                if not (pos in [2, 5] and i % 7 == 0):
                    bpy.ops.mesh.primitive_cube_add(size=1, location=(i * 7 + pos, 1, 0.4))
                    key_object = bpy.context.object
                    key_object.name = f"BlackKey_{black_key_midi_numbers[midi_index]}"
                    key_object.scale = (0.6, 2.5, 1.8)  
                    key_object.data.materials.append(black_material)
                    midi_index += 1


def animate_keys(notes):
    fps = 24  # Frames per second
    press_duration_frames = 1  # Frames taken to press the key down
    release_duration_frames = 1  # Frames taken to release the key
    key_depth = 0.7  # Depth to which the key is pressed down (black are 0.8 tall so to leave a little bit of space -0.1)

    for note, start_time, end_time in notes:
        key_object = bpy.data.objects.get(f"WhiteKey_{note}") or bpy.data.objects.get(f"BlackKey_{note}")
        if key_object and start_time < end_time:
            start_frame = convert_time_to_frame(start_time, fps)
            end_frame = convert_time_to_frame(end_time, fps)
            
            # Making sure end_frame is after start_frame + press and release durations
            min_end_frame = start_frame + press_duration_frames + release_duration_frames + 1
            if end_frame < min_end_frame:
                end_frame = min_end_frame
            
            original_z = key_object.location.z
            
            # Rest position 
            key_object.location.z = original_z
            key_object.keyframe_insert(data_path="location", frame=start_frame - 1)
            
            # Press down
            key_object.location.z = original_z - key_depth
            key_object.keyframe_insert(data_path="location", frame=start_frame + press_duration_frames)
            
            # Hold down
            key_object.location.z = original_z - key_depth
            key_object.keyframe_insert(data_path="location", frame=end_frame - release_duration_frames)
            
            # Release up
            key_object.location.z = original_z
            key_object.keyframe_insert(data_path="location", frame=end_frame)
            
            # Setting interpolation to linear
            if key_object.animation_data and key_object.animation_data.action:
                for fcurve in key_object.animation_data.action.fcurves:
                    for keyframe_point in fcurve.keyframe_points:
                        keyframe_point.interpolation = 'LINEAR'
