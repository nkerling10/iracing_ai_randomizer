## Standard library imports
import logging
import os
import platform
import random
import time
from pathlib import Path
from enum import Enum

## Third party imports
import irsdk
import sounddevice as sd
import soundfile as sf

## Local imports

audio_device = "Speakers (Realtek(R) Audio), MME"


class SessionName(Enum):
    INVALID = 0
    GET_IN_CAR = 1
    WARMUP = 2
    PARADE_LAPS = 3
    RACING = 4
    CHECKERED = 5
    COOLDOWN = 6


class RaceService:
    @staticmethod
    def _get_flag(flag):
        """
        Big thanks to `fruzyna` for this function
            source: https://github.com/fruzyna/iracing-apps

        Determines the current flag status of the race.
        """
        if flag & irsdk.Flags.checkered:
            return "checkered"
        else:
            if flag & irsdk.Flags.blue:
                return "blue"
            elif flag & irsdk.Flags.black:
                return "black"
            elif flag & irsdk.Flags.furled:
                return "gray"
            elif flag & irsdk.Flags.red:
                return "red"
            elif flag & irsdk.Flags.white:
                return "white"
            elif (
                flag & irsdk.Flags.yellow
                or flag & irsdk.Flags.yellow_waving
                or flag & irsdk.Flags.caution
                or flag & irsdk.Flags.caution_waving
                or flag & irsdk.Flags.debris
            ):
                return "yellow"
            elif flag & irsdk.Flags.green or flag & irsdk.Flags.green_held:
                return "green"
            else:
                return "green"

    @staticmethod
    def _pit_penalty(cls, race_manager, car_num):
        """
        Select and issue a pit penalty to designated car number
        """
        penalty = random.choice(
            race_manager.race_settings.penalties_player
            if car_num == race_manager.race_weekend.player_car_num
            else race_manager.race_settings.penalties
        )

        race_manager.ir.freeze_var_buffer_latest()
        flag_color = cls._get_flag(race_manager.ir["SessionFlags"])

        if flag_color == "green":
            logging.info(f"PENALTY: Passthrough for #{car_num}: {penalty}")
            race_manager._send_iracing_command(f"!bl {car_num} D")
            penalty_message = f"Passthrough PENALTY #{car_num}: {penalty}"
        elif flag_color == "yellow":
            logging.info(f"PENALTY: EOL for #{car_num}: {penalty}")
            race_manager._send_iracing_command(f"!eol {car_num}")
            penalty_message = f"EOL PENALTY #{car_num}: {penalty}"
        race_manager._send_iracing_command(penalty_message)

    @staticmethod
    def _issue_pre_race_penalty(race_manager):
        """
        Issue a pre-race penalty to each defined car
        """
        for car_num, penalty in race_manager.race_weekend.pre_race_penalties:
            if penalty in ["Failed Inspection x2", "Unapproved Adjustments"]:
                logging.info(f"#{car_num} to the rear: {penalty}")
                race_manager._send_iracing_command(f"!eol {car_num}")
                penalty_message = f"PENALTY: #{car_num} to the rear: {penalty}"
            elif penalty in ["Failed Inspection x3"]:
                logging.info(f"#{car_num} to the rear plus drivethrough: {penalty}")
                race_manager._send_iracing_command(f"!eol {car_num}")
                race_manager._send_iracing_command(f"!bl {car_num} D")
                penalty_message = f"PENALTY: #{car_num} to the rear plus drivethrough penalty: {penalty}"
            race_manager._send_iracing_command(penalty_message)

    @staticmethod
    def _play_sound():
        """
        Plays packaged sound file of start engine command
        """
        if sd.query_devices(device=audio_device):
            logging.debug(f"Setting audio output to {audio_device}")
            sd.default.device = audio_device
        logging.debug("Trying to play sound file")
        try:
            data, fs = sf.read(
                Path(f"{os.getcwd()}\\src\\assets\\sounds\\start-your-engines.wav"),
                dtype="float32",
            )
            sd.play(data, fs)
            logging.debug("Sound played successfully")
        except Exception as e:
            logging.error(f"{e.__class__.__name__}: {e}")

    @classmethod
    def _pre_race_actions(cls, race_manager):
        """
        Executes pre-race actions to:
            1. Play engine start command
            2. Start the grid/parade laps
            3. Issue calculated pre-race penalties
        """
        ## Play start engine command
        cls._play_sound()
        logging.debug("Sleeping for 30 seconds while sound plays")
        time.sleep(30)
        ## This will change session state from 2 -> 3
        ## warmup -> parade_laps
        logging.debug("Issuing gridstart command")
        race_manager._send_iracing_command("!gridstart")
        time.sleep(10)
        ## Wait for cars to get rolling, then issue any pre-race penalties
        if len(race_manager.race_weekend.pre_race_penalties) > 0:
            logging.debug("Issuing pre-race penalties")
            cls._issue_pre_race_penalty(race_manager)
        else:
            logging.debug("No pre-race penalties to issue")
        logging.info("Pre-race actions are complete")
        logging.debug(
            f"Stage lengths: \
                      {race_manager.race_weekend.stage_1.stage_end_lap}/ \
                      {race_manager.race_weekend.stage_2.stage_end_lap}/ \
                      {race_manager.race_weekend.stage_3.stage_end_lap}"
        )
        race_manager._send_iracing_command(
            f"Stage lengths: \
                                           {race_manager.race_weekend.stage_1.stage_end_lap}/ \
                                           {race_manager.race_weekend.stage_2.stage_end_lap}/ \
                                           {race_manager.race_weekend.stage_3.stage_end_lap}"
        )

    @classmethod
    def _process_race(cls, race_manager):
        # handle stage 1
        logging.debug(
            f"Starting tracking of Stage 1 - ends on lap {race_manager.race_weekend.stage_1.stage_end_lap}"
        )
        # handle stage 2
        logging.debug(
            f"Starting tracking of Stage 2 - ends on lap {race_manager.race_weekend.stage_2.stage_end_lap}"
        )
        # handle stage 3
        logging.debug(
            f"Starting tracking of Stage 3 - ends on lap {race_manager.race_weekend.stage_3.stage_end_lap}"
        )

        quit()

    @classmethod
    def race(cls, race_manager):
        while True:
            # race_manager.ir.freeze_var_buffer_latest()
            ## Enum is useful to map session state id to its name
            logging.debug(
                f"Session state is {SessionName(race_manager.ir["SessionState"]).name}"
            )
            ## Loop until player enters the car
            while True:
                # race_manager.ir.freeze_var_buffer_latest()
                ## Session state GET_IN_CAR
                if race_manager.ir["SessionState"] == 1:
                    time.sleep(1)
                else:
                    break
            ## Session state WARMUP (sitting on pitroad waiting for cars to grid)
            ## Session state PARADE_LAPS is also handled in this logic
            if race_manager.ir["SessionState"] == 2:
                ## Perform pre-race actions
                cls._pre_race_actions(race_manager)
            ## Pre-race penalties will finish being issued before session state
            ## changes from 3 -> 4. Just sleep and wait until the race starts
            elif race_manager.ir["SessionState"] == 3:
                time.sleep(1)
            ## Session state RACING
            elif race_manager.ir["SessionState"] == 4:
                logging.debug("Race has started!")
                cls._process_race(race_manager)
            ## Session state CHECKERED
            elif race_manager.ir["SessionState"] == 5:
                pass
            ## Session state COOLDOWN
            elif race_manager.ir["SessionState"] == 6:
                pass
            else:
                logging.warning(
                    f"Unexpected issue: session state is \
                                {race_manager.ir["SessionState"]}"
                )
