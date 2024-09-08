bl_info = {
    "name": "Piano Animation",
    "blender": (4, 0, 0),
    "category": "Animation",
}

import bpy
import os
import mido

class PianoAnimationPreferences(bpy.types.PropertyGroup):
    use_imported_model: bpy.props.BoolProperty(
        name="Use Imported Model",
        description="Animate an already imported piano model",
        default=False,
    )
    midi_filepath: bpy.props.StringProperty(
        name="MIDI File Path",
        description="Path to the MIDI file",
        subtype="FILE_PATH"
    )
    mp3_filepath: bpy.props.StringProperty(
        name="MP3 File Path",
        description="Path to the MP3 file to play in the background",
        subtype="FILE_PATH"
    )

class PianoAnimationOperator(bpy.types.Operator):
    bl_idname = "object.piano_animation_operator"
    bl_label = "Create Piano Animation"

    def execute(self, context):
        preferences = context.scene.piano_animation_prefs
        midi_filepath = preferences.midi_filepath
        mp3_filepath = preferences.mp3_filepath
        
        if not midi_filepath or not os.path.isfile(midi_filepath):
            self.report({'ERROR'}, "MIDI file path is not set or file does not exist.")
            return {'CANCELLED'}
        
        if not mp3_filepath or not os.path.isfile(mp3_filepath):
            self.report({'ERROR'}, "MP3 file path is not set or file does not exist.")
            return {'CANCELLED'}
        
        notes = parse_midi(midi_filepath)
        
        if not preferences.use_imported_model:
            create_piano_keys_and_base(context)
            
        animate_keys(notes)
        
        # Add MP3 background music
        if mp3_filepath:
            add_background_music(mp3_filepath)

        # Update the end frame based on the last note's end time
        if notes:
            last_note = max(notes, key=lambda n: n[2])  # Get the note with the latest end time
            last_frame = convert_time_to_frame(last_note[2])
            bpy.context.scene.frame_start = 0
            bpy.context.scene.frame_end = last_frame # Dynamically set the last frame based on the length of the midi

        return {'FINISHED'}

# UI Panel
class PianoAnimationPanel(bpy.types.Panel):
    bl_label = "Piano Animation"
    bl_idname = "VIEW3D_PT_piano_animation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Animation"

    def draw(self, context):
        layout = self.layout
        preferences = context.scene.piano_animation_prefs

        # Checkbox to choose between imported or new model
        layout.prop(preferences, "use_imported_model")

        # Show naming instructions if using imported model
        if preferences.use_imported_model:
            layout.label(text="Make sure keys are named 'WhiteKey_21', 'BlackKey_22', 'WhiteKey_23'... starting with 21 for the first white key (A0).", icon='ERROR')

        # Input for MIDI file
        layout.prop(preferences, "midi_filepath", text="MIDI File")

        # Input for MP3 file
        layout.prop(preferences, "mp3_filepath", text="MP3 File")

        # Button to trigger the operator
        layout.operator(PianoAnimationOperator.bl_idname)

# Menu to add operator
def menu_func(self, context):
    self.layout.operator(PianoAnimationOperator.bl_idname)

# Register Function
def register():
    bpy.utils.register_class(PianoAnimationPreferences)
    bpy.utils.register_class(PianoAnimationOperator)
    bpy.utils.register_class(PianoAnimationPanel)
    bpy.types.VIEW3D_MT_object.append(menu_func)
    
    # Add the Property Group to the Scene
    bpy.types.Scene.piano_animation_prefs = bpy.props.PointerProperty(type=PianoAnimationPreferences)

# Unregister Function
def unregister():
    bpy.utils.unregister_class(PianoAnimationPreferences)
    bpy.utils.unregister_class(PianoAnimationOperator)
    bpy.utils.unregister_class(PianoAnimationPanel)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

    del bpy.types.Scene.piano_animation_prefs

if __name__ == "__main__":
    register()

# Parse midi file into dictionary of 'notes'
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

def animate_keys(notes):
    fps = 24
    press_duration_frames = 1
    release_duration_frames = 1

    first_white_key = bpy.data.objects.get("WhiteKey_21") 
    if first_white_key:
        white_key_height = first_white_key.dimensions.z  
        key_depth = 0.8 * white_key_height # Based on white key because black keys are twice the height             
    else:
        raise ValueError("First white key not found. Ensure that your keys are named correctly.") # Inform user that the naming is incorrect

    for note, start_time, end_time in notes:
        key_object = bpy.data.objects.get(f"WhiteKey_{note}") or bpy.data.objects.get(f"BlackKey_{note}") # Select piano key based on midi number name

        if key_object and start_time < end_time:
            
            # Convert time to frame
            start_frame = convert_time_to_frame(start_time, fps)
            end_frame = convert_time_to_frame(end_time, fps)

            # Make sure there is enough time for animation
            min_end_frame = start_frame + press_duration_frames + release_duration_frames + 1
            if end_frame < min_end_frame:
                end_frame = min_end_frame

            # Remember original position
            original_z = key_object.location.z

            # Key in regular position
            key_object.location.z = original_z
            key_object.keyframe_insert(data_path="location", frame=start_frame - 1)

            # Key pressed
            key_object.location.z = original_z - key_depth
            key_object.keyframe_insert(data_path="location", frame=start_frame + press_duration_frames)

            # Key held down
            key_object.location.z = original_z - key_depth
            key_object.keyframe_insert(data_path="location", frame=end_frame - release_duration_frames)

            # Key released
            key_object.location.z = original_z
            key_object.keyframe_insert(data_path="location", frame=end_frame)

            if key_object.animation_data and key_object.animation_data.action:
                for fcurve in key_object.animation_data.action.fcurves:
                    for keyframe_point in fcurve.keyframe_points:
                        keyframe_point.interpolation = 'LINEAR'

def convert_time_to_frame(time, fps=24):
    return int(time * fps)

def create_material(name, color):
    material = bpy.data.materials.new(name=name)
    material.diffuse_color = color
    return material

# Function to create the piano model if selected
def create_piano_keys_and_base(context):
    # Create white material
    white_material = create_material("WhiteMaterial", (1, 1, 1, 1))
    # Create black material
    black_material = create_material("BlackMaterial", (0, 0, 0, 1))
    # Create base material
    base_material = create_material("BaseMaterial", (0.25, 0.1, 0.05, 1)) 
    
    # Create base
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -1))
    base_object = bpy.context.object
    base_object.scale = (52, 5, 1)
    base_object.name = "PianoBase"
    base_object.data.materials.append(base_material)

    # Create white keys
    # (21 = A)
    white_key_midi_numbers = [21, 23, 24, 26, 27, 29, 31, 33, 34, 36, 37, 39, 41, 43, 44, 46, 47, 49, 51, 53, 54, 56, 57, 59, 61, 63, 64, 66, 67, 69, 71, 73, 74, 76, 77, 79, 81, 83, 84, 86, 88, 90, 91, 93, 95, 97, 98, 100, 102, 104, 105]
    for i in range(len(white_key_midi_numbers)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(i - 25.5, 0, 0))
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
                    bpy.ops.mesh.primitive_cube_add(size=1, location=(i * 7 + pos - 25.5, 1, 0.4))
                    key_object = bpy.context.object
                    key_object.name = f"BlackKey_{black_key_midi_numbers[midi_index]}"
                    key_object.scale = (0.6, 2.5, 1.8)  
                    key_object.data.materials.append(black_material)
                    midi_index += 1

def add_background_music(mp3_filepath):
    if bpy.context.scene.sequence_editor is None:
        bpy.context.scene.sequence_editor_create()

    # Clear existing strips
    for strip in bpy.context.scene.sequence_editor.sequences_all:
        bpy.context.scene.sequence_editor.sequences.remove(strip)

    # Add MP3 strip
    bpy.context.scene.sequence_editor.sequences.new_sound(name="BackgroundMusic", filepath=mp3_filepath, channel=1, frame_start=0)