This poker engine solves properly for HULH and NLHE but our ES MCCFR cannot converge leduc poker. Vanilla CFR AND chance sampling does.

I've exhaustively verified the correctness of our leduc implementation against ground truths (Open-spiel).

Here's the code:

crates/engine/src/position.rs:
```
//! Type-safe position-aware system that enforces evaluation from all positions.
//!
//! This module provides types that make position bias impossible at compile time.
//! The core abstraction is `PositionFair<T>` which can only be constructed by
//! evaluating from ALL positions, preventing cherry-picking favorable positions.

use crate::types::PlayerId;
use std::fmt::{self, Debug, Display};

/// A seat number represents a fixed physical position at the table.
/// Seats are numbered 0, 1, 2, ... and never change during a game.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct SeatNumber(pub usize);

impl SeatNumber {
    pub fn new(seat: usize) -> Self {
        Self(seat)
    }
    
    pub fn as_usize(&self) -> usize {
        self.0
    }
}

impl Display for SeatNumber {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Seat{}", self.0)
    }
}

impl From<usize> for SeatNumber {
    fn from(seat: usize) -> Self {
        SeatNumber(seat)
    }
}

/// A relative position represents a player's position relative to the dealer button.
/// 0 = dealer button, 1 = one seat after button, etc.
/// This changes every hand as the button moves.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct RelativePosition(pub u8);

impl RelativePosition {
    pub fn new(position: u8) -> Self {
        Self(position)
    }
    
    pub fn as_u8(&self) -> u8 {
        self.0
    }
    
    /// Calculate relative position from seat number and button position.
    /// Formula: (seat_number - button_seat + num_players) % num_players
    pub fn from_seat_and_button(seat: SeatNumber, button: ButtonSeat, num_players: usize) -> Self {
        let relative = (seat.0 + num_players - button.0.0) % num_players;
        Self(relative as u8)
    }
    
    /// Alias for from_seat_and_button to match the plan
    pub fn calculate(seat: SeatNumber, button_seat: SeatNumber, num_players: usize) -> Self {
        Self::from_seat_and_button(seat, ButtonSeat::new(button_seat), num_players)
    }
    
    pub fn is_button(&self) -> bool {
        self.0 == 0
    }
}

impl Display for RelativePosition {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Pos{}", self.0)
    }
}

/// The seat where the dealer button is currently located.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct ButtonSeat(pub SeatNumber);

impl ButtonSeat {
    pub fn new(seat: SeatNumber) -> Self {
        Self(seat)
    }
    
    pub fn as_seat_number(&self) -> SeatNumber {
        self.0
    }
    
    /// Alias for as_seat_number to match the plan
    pub fn seat(&self) -> SeatNumber {
        self.0
    }
    
    /// Advance the button to the next seat.
    pub fn advance(&mut self, num_players: usize) {
        self.0 = SeatNumber((self.0.0 + 1) % num_players);
    }
}

impl Display for ButtonSeat {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Button@{}", self.0)
    }
}

/// A position-aware wrapper that FORCES evaluation from all positions.
/// 
/// This type can only be constructed by evaluating from ALL positions,
/// and provides no access to individual position results - only aggregates.
/// This design prevents position bias by making it impossible to evaluate
/// from a single position or cherry-pick favorable results.
/// 
/// # Usage in Evaluation
/// All evaluation functions (exploitability, nash_conv, LBR, bot evaluation)
/// should return `PositionFair<T>` to ensure position-fair evaluation:
/// 
/// ```rust,ignore
/// use engine::{Game, PositionFair};
/// 
/// pub fn calculate_exploitability(game: &Game) -> PositionFair<f64> {
///     PositionFair::evaluate_all(game.num_players(), |pos| {
///         // Evaluate from position `pos`
///         Ok(0.0) // placeholder
///     }).unwrap()
/// }
/// ```
#[derive(Debug, Clone)]
pub struct PositionFair<T> {
    evaluations: Vec<T>,
    positions: usize,
}

impl<T> PositionFair<T> {
    /// Can only be constructed by evaluating from ALL positions.
    /// 
    /// # Arguments
    /// * `num_positions` - Number of positions to evaluate
    /// * `evaluator` - Function that evaluates at each position
    /// 
    /// # Example
    /// ```rust,ignore
    /// use engine::PositionFair;
    /// 
    /// let result = PositionFair::<f64>::evaluate_all(2, |pos| {
    ///     // Evaluate at position `pos`
    ///     Ok(pos as f64 * 10.0) // placeholder evaluation
    /// }).unwrap();
    /// ```
    pub fn evaluate_all<F, E>(
        num_positions: usize,
        mut evaluator: F,
    ) -> Result<Self, E>
    where
        F: FnMut(usize) -> Result<T, E>,
    {
        let mut evaluations = Vec::with_capacity(num_positions);
        for pos in 0..num_positions {
            evaluations.push(evaluator(pos)?);
        }
        Ok(Self { evaluations, positions: num_positions })
    }
    
    /// Forces consumer to handle all positions through aggregation.
    /// 
    /// There is no way to access individual position results - you must
    /// aggregate them to get a final value.
    /// 
    /// # Example
    /// ```rust,ignore
    /// use engine::PositionFair;
    /// 
    /// let result = PositionFair::<f64>::evaluate_all(2, |pos| {
    ///     Ok(pos as f64 * 10.0)
    /// }).unwrap();
    /// 
    /// let avg = result.aggregate(|values| {
    ///     values.iter().sum::<f64>() / values.len() as f64
    /// });
    /// ```
    pub fn aggregate<R, F>(self, aggregator: F) -> R
    where
        F: FnOnce(Vec<T>) -> R,
    {
        aggregator(self.evaluations)
    }
    
    /// Returns the number of positions that were evaluated.
    pub fn num_evaluations(&self) -> usize {
        self.positions
    }
}

/// Type-safe position rotation schedule for training.
/// 
/// Manages automatic rotation through all positions to ensure
/// each player learns from every position equally.
#[derive(Debug, Clone)]
pub struct RotationSchedule {
    num_positions: usize,
    button: ButtonSeat,
}

impl RotationSchedule {
    /// Creates a new rotation schedule.
    pub fn new(num_positions: usize) -> Self {
        Self { 
            num_positions, 
            button: ButtonSeat::new(SeatNumber(0))
        }
    }
    
    /// Returns position mapping for current iteration.
    pub fn get_mapping(&self) -> PositionMapping {
        PositionMapping::from_button(self.button, self.num_positions)
    }
    
    /// Advances to the next position in the rotation.
    pub fn advance(&mut self) {
        self.button.advance(self.num_positions);
    }
    
    /// Returns the current dealer position.
    pub fn current_dealer(&self) -> usize {
        self.button.0.0
    }
    
    /// Returns the current button seat.
    pub fn current_button(&self) -> ButtonSeat {
        self.button
    }
}

/// Immutable position mapping for a single iteration.
/// 
/// Maps between logical players and physical seat positions,
/// accounting for dealer button rotation.
#[derive(Debug, Clone, Copy)]
pub struct PositionMapping {
    button: ButtonSeat,
    num_players: usize,
}

impl PositionMapping {
    /// Creates a new position mapping.
    pub fn new(dealer_button: usize, num_players: usize) -> Self {
        Self { 
            button: ButtonSeat::new(SeatNumber(dealer_button)),
            num_players 
        }
    }
    
    /// Creates a new position mapping from typed button seat.
    pub fn from_button(button: ButtonSeat, num_players: usize) -> Self {
        Self { button, num_players }
    }
    
    /// Maps a logical player ID to their physical seat position.
    pub fn player_to_seat(&self, player: PlayerId) -> SeatNumber {
        SeatNumber((player + self.button.0.0) % self.num_players)
    }
    
    /// Maps a physical seat position to the logical player ID.
    pub fn seat_to_player(&self, seat: SeatNumber) -> PlayerId {
        (seat.0 + self.num_players - self.button.0.0) % self.num_players
    }
    
    /// Returns the dealer button position.
    pub fn dealer_button(&self) -> usize {
        self.button.0.0
    }
    
    /// Returns the dealer button as ButtonSeat type.
    pub fn button_seat(&self) -> ButtonSeat {
        self.button
    }
    
    /// Returns the number of players.
    pub fn num_players(&self) -> usize {
        self.num_players
    }
    
    /// Gets the relative position for a seat.
    pub fn seat_to_relative_position(&self, seat: SeatNumber) -> RelativePosition {
        RelativePosition::from_seat_and_button(seat, self.button, self.num_players)
    }
    
    /// Alias for seat_to_relative_position to match the plan
    pub fn get_relative_position(&self, seat: SeatNumber) -> RelativePosition {
        self.seat_to_relative_position(seat)
    }
}


#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_position_fair_forces_all_evaluations() {
        let result = PositionFair::evaluate_all(3, |pos| {
            Ok::<_, ()>(pos * 10)
        }).unwrap();
        
        assert_eq!(result.num_evaluations(), 3);
        
        let sum = result.aggregate(|values| {
            values.iter().sum::<usize>()
        });
        assert_eq!(sum, 0 + 10 + 20);
    }
    
    #[test]
    fn test_rotation_schedule() {
        let mut rotation = RotationSchedule::new(2);
        
        assert_eq!(rotation.current_dealer(), 0);
        let mapping1 = rotation.get_mapping();
        assert_eq!(mapping1.dealer_button(), 0);
        
        rotation.advance();
        assert_eq!(rotation.current_dealer(), 1);
        
        rotation.advance();
        assert_eq!(rotation.current_dealer(), 0); // Wraps around
    }
    
    #[test]
    fn test_position_mapping() {
        let mapping = PositionMapping::new(1, 2); // Dealer at position 1
        
        // Player 0 should be at seat 1
        assert_eq!(mapping.player_to_seat(0), SeatNumber(1));
        // Player 1 should be at seat 0
        assert_eq!(mapping.player_to_seat(1), SeatNumber(0));
        
        // Reverse mapping
        assert_eq!(mapping.seat_to_player(SeatNumber(0)), 1);
        assert_eq!(mapping.seat_to_player(SeatNumber(1)), 0);
    }
    
    #[test]
    fn test_relative_position_calculation() {
        // 3-player game, button at seat 1
        let button = ButtonSeat::new(SeatNumber(1));
        
        // Seat 0: (0 - 1 + 3) % 3 = 2
        assert_eq!(
            RelativePosition::from_seat_and_button(SeatNumber(0), button, 3),
            RelativePosition(2)
        );
        
        // Seat 1 (button): (1 - 1 + 3) % 3 = 0
        assert_eq!(
            RelativePosition::from_seat_and_button(SeatNumber(1), button, 3),
            RelativePosition(0)
        );
        
        // Seat 2: (2 - 1 + 3) % 3 = 1
        assert_eq!(
            RelativePosition::from_seat_and_button(SeatNumber(2), button, 3),
            RelativePosition(1)
        );
    }
    
    #[test]
    fn test_button_advance() {
        let mut button = ButtonSeat::new(SeatNumber(0));
        
        // In a 3-player game
        button.advance(3);
        assert_eq!(button.as_seat_number(), SeatNumber(1));
        
        button.advance(3);
        assert_eq!(button.as_seat_number(), SeatNumber(2));
        
        button.advance(3);
        assert_eq!(button.as_seat_number(), SeatNumber(0)); // Wraps around
    }
    
    #[test]
    fn test_type_display() {
        assert_eq!(format!("{}", SeatNumber(2)), "Seat2");
        assert_eq!(format!("{}", RelativePosition(1)), "Pos1");
        assert_eq!(format!("{}", ButtonSeat::new(SeatNumber(0))), "Button@Seat0");
    }
    
}
```

crates/games/src/hulh/action.rs:
```
//! Defines the betting actions specific to HULH.
//!
//! ## POKER RULES: Action Terminology
//! 
//! - **CALL**: Match the current stakes (0 if no bet pending)
//! - **RAISE**: Increase the stakes (opening bet or re-raise)
//! - **FOLD**: Surrender the hand
//! 
//! ### IMPORTANT: Unified CALL Action
//! The CALL action is overloaded based on game state:
//! - When facing a bet: CALL matches the current bet
//! - When NOT facing a bet: CALL contributes 0 (equivalent to check)
//! This reduces action space complexity while maintaining semantic clarity.

use engine::types::ConcreteAction;

#[repr(u32)]
#[derive(Copy, Clone, Debug, Eq, PartialEq, Hash)]
/// Betting verbs for Heads‑Up Limit Hold'em and variants.
///
/// Simple fixed-limit actions only.
pub enum HulhMove {
	Fold = 0,
	Call = 1,  // Overloaded: matches current stakes (0 if no bet)
	Raise = 2, // Fixed raise amount determined by settings
}

impl From<HulhMove> for ConcreteAction {
	#[inline]
	fn from(m: HulhMove) -> Self {
		ConcreteAction(m as u64)
	}
}

// ---------------------------------------------------------------------
// Legacy integer constants and new action constants
// ---------------------------------------------------------------------

/// Equivalent to `HulhMove::Fold.into()`.
pub const FOLD_ACTION: ConcreteAction = ConcreteAction(HulhMove::Fold as u64);

/// Equivalent to `HulhMove::Call.into()`.
/// When facing a bet: matches the current bet.
/// When NOT facing a bet: contributes 0 (check).
pub const CALL_ACTION: ConcreteAction = ConcreteAction(HulhMove::Call as u64);

/// Equivalent to `HulhMove::Raise.into()`.
pub const RAISE_ACTION: ConcreteAction = ConcreteAction(HulhMove::Raise as u64);

/// The canonical action grid for HULH Poker and its variants.
/// This grid defines the set of all possible actions.
/// The legality of each action is determined by the game state and settings.
pub const GRID_HULH: &[ConcreteAction] = &[
	FOLD_ACTION,       // Index 0
	CALL_ACTION,       // Index 1 (handles both call and check)
	RAISE_ACTION,      // Index 2
];

```

crates/games/src/hulh/constants.rs:
```
//! HULH game constants (players, rounds, blinds, etc.).

// Removed unused import: use crate::Chips;
use engine::types::{ConcreteAction, PlayerId}; // Keep engine types needed

/// Upper bound for table capacity (Phase-0)
pub const MAX_SEATS: usize = 10;
// Game structure

pub const MAX_HOLE_CARDS: usize = 2;
pub const MAX_BOARD_CARDS: usize = 5; // 3 + 1 + 1

/// Maximum actions one betting round can contain in fixed‑limit HULH.
/// Increased from 11 to 22 to accommodate potentially long betting sequences
/// generated by random simulations in tests like `mask_roundtrip_hulh`.
/// Further increased to 30 to handle edge cases in multiplayer games.
/// Original calculation: SB/BB + 4 raises (each raise is "raise + call") + final check/call ≈ 11.
pub const MAX_ACTIONS_PER_ROUND: usize = 30; // Increased from 22

// // Betting structure (Standard HULH)
// // Raise sizes: Round 0/1 (Pre-flop/Flop) = BB, Round 2/3 (Turn/River) = 2*BB
// pub const BROKEN_RAISE_SIZES: [Chips; BROKEN_NUM_ROUNDS] = [
//     BROKEN_BIG_BLIND, // Pre-flop raise amount (same as BB)
//     BROKEN_BIG_BLIND, // Flop raise amount
//     BROKEN_BIG_BLIND * 2, // Turn raise amount
//     BROKEN_BIG_BLIND * 2, // River raise amount
// ];
// Max raises per round (standard HULH) - REMOVED CONSTANT
// pub const BROKEN_MAX_RAISES: [usize; BROKEN_NUM_ROUNDS] = [3, 4, 4, 4];
// BROKEN_FLOAT_TOLERANCE removed

// pub const STARTING_STACK: Chips = 3000;

// ------------------------------------------------------------
// Lightweight replacement for `approx::abs_diff_eq!` (REMOVED)
// ------------------------------------------------------------

// abs_diff_eq! macro removed

// Player roles (relative to button)
// pub const BROKEN_SB_PLAYER: PlayerId = 0; // Small Blind acts first post-flop
// pub const BROKEN_BB_PLAYER: PlayerId = 1; // Big Blind acts first pre-flop

// Action constants are removed in favor of HulhMove enum

// Sentinel value for betting sequence array initialization
pub const BETTING_SEQ_SENTINEL: ConcreteAction = ConcreteAction(u64::MAX - 1);

// ------------------------------------------------------------
// Seating helpers
// ------------------------------------------------------------

#[inline]
pub const fn small_blind(btn: PlayerId, n: usize) -> PlayerId {
	if n == 2 {
		btn
	} else {
		(btn + 1) % n
	}
}
#[inline]
pub const fn big_blind(btn: PlayerId, n: usize) -> PlayerId {
	if n == 2 {
		(btn + 1) % n
	} else {
		(btn + 2) % n
	}
}
#[inline]
pub const fn first_to_act_preflop(btn: PlayerId, n: usize) -> PlayerId {
	if n == 2 {
		btn
	} else {
		(big_blind(btn, n) + 1) % n
	}
}
/// Returns the seat that acts first *after the flop*.
///
/// Standard poker rules dictate the order of action post-flop:
///   - In heads-up play (N=2), the player who is *not* on the button (the Big Blind) acts first.
///   - In multi-way games (N>=3), the first active player clockwise from the button (the Small Blind) acts first.
///
/// This function implements these standard rules.
#[inline]
pub const fn first_to_act_postflop(btn: PlayerId, n: usize) -> PlayerId {
	// NOTE: eprintln! is not allowed in const fn, so we cannot print here.
	// If you want to debug, add prints in the calling code.

	match n {
		2 => big_blind(btn, n),   // HU: big blind opens (button is SB)
		_ => small_blind(btn, n), // 3-handed or more: small blind opens
	}
}



```

crates/games/src/hulh/game.rs:
```
//! Defines the top-level HulhGame struct and Game trait implementation.

use crate::hulh::{
	constants::MAX_SEATS,   // Import specific constant
	settings::HulhSettings, // <-- Import HulhSettings from new module
	state::core::HulhState,
	utils, // <-- Import the new utils module
};
use engine::{
	game::Game,
	position_context::get_position_context,
	types::Utility, // Keep Utility
};

// --- HulhGame Struct ---

use cfr_rng::CfrRngPool; // Added import

#[derive(Debug, Clone)] // Removed Default derive
pub struct HulhGame {
	// Store settings internally
	settings: HulhSettings,
	// Cached utility bounds
	cached_min_utility: Utility,
	cached_max_utility: Utility,
}

impl HulhGame {
	/// Creates a new HULH game with the specified number of players.
	pub fn new_with_players(n: usize) -> Self {
		assert!(
			(2..=MAX_SEATS).contains(&n),
			"HULH supports 2…{} seats",
			MAX_SEATS
		);

		// Initialize settings with only non-positional configuration
		let settings = HulhSettings {
			num_players: n,
			vector_cards: false,
			..Default::default()
		};

		let max_commit_val = utils::calculate_max_commitment(&settings);
		let min_util = -(max_commit_val as Utility);
		let max_util = {
			let num_opponents = settings.num_players.saturating_sub(1) as Utility;
			if settings.num_players > 1 {
				num_opponents * (max_commit_val as Utility)
			} else {
				max_commit_val as Utility
			}
		};

		Self {
			settings,
			cached_min_utility: min_util,
			cached_max_utility: max_util,
		}
	}

	/// Creates a new HULH game with the specified settings.
	pub fn new_with_settings(settings: HulhSettings) -> Self {
		let max_commit_val = utils::calculate_max_commitment(&settings);
		let min_util = -(max_commit_val as Utility);
		let max_util = {
			let num_opponents = settings.num_players.saturating_sub(1) as Utility;
			// Ensure num_opponents is not zero before multiplication to avoid NaN or incorrect results if max_commit_val is large.
			if settings.num_players > 1 {
				// Check num_players directly
				num_opponents * (max_commit_val as Utility)
			} else {
				// Single player game
				max_commit_val as Utility // Or 0.0, depending on 1-player game semantics. Using max_commit_val for now.
			}
		};
		Self {
			settings,
			cached_min_utility: min_util,
			cached_max_utility: max_util,
		}
	}

	/// Returns the number of players configured for this game.
	#[inline]
	pub fn num_players(&self) -> usize {
		self.settings.num_players
	}
	// max_commitment method is removed from here
}

impl Game for HulhGame {
	type State = HulhState;
	type Settings = HulhSettings;

	fn new_initial_state(&self, rng_pool: &mut CfrRngPool) -> Self::State {
		// Check thread-local position context first
		let dealer_btn = if let Some(mapping) = get_position_context() {
			log::trace!("Creating HULH initial state with position mapping: dealer at {}", mapping.dealer_button());
			mapping.dealer_button()
		} else {
			// PANIC to prevent position bias - position context is required
			panic!(
				"Creating HULH state without position context - this would introduce position bias! \
				You must use PositionFair wrapper or set position context explicitly."
			);
		};
		HulhState::new(self, dealer_btn, rng_pool)
	}

	fn num_players(&self) -> usize {
		self.settings.num_players
	}

	fn settings(&self) -> &Self::Settings {
		&self.settings
	}

	fn rules_summary(&self) -> String {
		format!(
			"HULH ({}-player, SB={}, BB={}, Stack={}, Ante={}, Deck={:?}, RaiseRule={:?})",
			self.num_players(),
			self.settings.small_blind,
			self.settings.big_blind,
			self.settings.starting_stack,
			self.settings.ante,
			self.settings.deck_type,
			self.settings.raise_rule
		)
	}

	fn max_utility(&self) -> Utility {
		self.cached_max_utility
	}

	fn min_utility(&self) -> Utility {
		self.cached_min_utility
	}
	fn utility_sum(&self) -> Utility {
		0.0
	}
}

// ------------------------------------------------------------------
//  Convenience: provide `Default` to preserve older call-sites such as
//  experimental binaries and benches that still rely on
//  `HulhGame::default()`.
// ------------------------------------------------------------------
impl Default for HulhGame {
	fn default() -> Self {
		Self::new_with_settings(HulhSettings::default())
	}
}


```

crates/games/src/hulh/mod.rs:
```
// pub mod abstraction; // Removed - action abstractions deleted
pub mod action;
pub mod constants;
pub mod game;
pub mod settings; // <-- Add settings module
pub mod state; // re‑exports core inside
mod undo; // keep private
pub mod utils; // <-- Add utils module
pub mod scripted; // Scripted game helper for testing

// Easy access for callers -----------------------------------------------
pub use action::HulhMove; // <‑‑ allow tests to import directly
pub use game::HulhGame;
pub use settings::{HulhGameRules, HulhSettings}; // <-- Use HulhSettings and HulhGameRules from settings module
pub use state::core::HulhState; // <‑‑ idem
pub use scripted::{HulhScriptedGame, HulhScriptedGameBuilder, Street, QuickAction, HandResult}; // Export scripted game types

// Legacy integer aliases (see `action.rs` for docs)
pub use action::{
	CALL_ACTION, FOLD_ACTION, RAISE_ACTION,
};
// Re-export grid constant
pub use action::GRID_HULH;

// Player index aliases ----------------------------------------------------
// These are role constants, not directly from settings.
// Their usage might need to be re-evaluated if player count changes behavior significantly.
pub use constants::{
	big_blind, first_to_act_postflop, first_to_act_preflop, small_blind,
};

```

crates/games/src/hulh/scripted.rs:
```
//! Scripted HULH game helper for testing
//! 
//! Provides a clean API for creating deterministic HULH game scenarios
//! with card control and easy action methods.

use crate::hulh::{
    HulhGame, HulhState, HulhSettings,
    CALL_ACTION, FOLD_ACTION, RAISE_ACTION,
};
use crate::Chips;
use anyhow::{Result, anyhow, bail};
use engine::{
    Game, State,
    types::{ConcreteAction, PlayerId},
    position_context::{set_position_context, clear_position_context},
    position::PositionMapping,
};
use fastcards::{Card, rigged_fast_deck::RiggedFastDeck, fast_deck::FastDeckTrait};
use cfr_rng::CfrRngPool;
use std::sync::{Arc, Mutex};
use std::collections::HashSet;
use std::fmt;

/// Result of a completed hand
#[derive(Debug, Clone)]
pub struct HandResult {
    pub winners: Vec<PlayerId>,
    pub pot_size: Chips,
    pub went_to_showdown: Vec<bool>,
}

/// Context for action tracking in metrics
#[derive(Debug, Clone)]
pub struct ActionContext {
    pub seat: usize,
    pub round: u8,
    pub action: ConcreteAction,
    pub amount: i32,
    pub facing_bet: bool,
    pub is_bb_option: bool,
}

/// Builder for creating a scripted HULH game
pub struct HulhScriptedGameBuilder {
    num_players: usize,
    button_position: Option<usize>,
    small_blind: Chips,
    big_blind: Chips,
    starting_stacks: Chips,
    hole_cards: Vec<Option<Vec<Card>>>,
    flop_cards: Option<Vec<Card>>,
    turn_card: Option<Card>,
    river_card: Option<Card>,
    metrics_collector: Option<Arc<Mutex<dyn MetricsCollector>>>,
}

/// Trait for metrics collection integration
pub trait MetricsCollector: Send + Sync {
    fn track_action(&mut self, context: ActionContext);
    fn start_hand(&mut self, button_position: usize);
    /// Finalize hand with results
    /// - went_to_showdown: which players made it to showdown
    /// - won_hand: which players won the hand (for WWSF tracking - includes all winners)
    fn finalize_hand(&mut self, button_position: usize, went_to_showdown: Vec<bool>, won_hand: Vec<bool>);
}

impl Default for HulhScriptedGameBuilder {
    fn default() -> Self {
        Self {
            num_players: 2,
            button_position: None,
            small_blind: 1,
            big_blind: 2,
            starting_stacks: 100,
            hole_cards: vec![],
            flop_cards: None,
            turn_card: None,
            river_card: None,
            metrics_collector: None,
        }
    }
}

impl fmt::Debug for HulhScriptedGameBuilder {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("HulhScriptedGameBuilder")
            .field("num_players", &self.num_players)
            .field("button_position", &self.button_position)
            .field("small_blind", &self.small_blind)
            .field("big_blind", &self.big_blind)
            .field("starting_stacks", &self.starting_stacks)
            .field("hole_cards", &self.hole_cards)
            .field("flop_cards", &self.flop_cards)
            .field("turn_card", &self.turn_card)
            .field("river_card", &self.river_card)
            .field("has_metrics_collector", &self.metrics_collector.is_some())
            .finish()
    }
}

impl HulhScriptedGameBuilder {
    pub fn new() -> Self {
        Self::default()
    }
    
    pub fn players(mut self, n: usize) -> Self {
        self.num_players = n;
        self
    }
    
    pub fn button_position(mut self, pos: usize) -> Self {
        self.button_position = Some(pos);
        self
    }
    
    pub fn small_blind(mut self, amount: Chips) -> Self {
        self.small_blind = amount;
        self
    }
    
    pub fn big_blind(mut self, amount: Chips) -> Self {
        self.big_blind = amount;
        self
    }
    
    pub fn starting_stacks(mut self, amount: Chips) -> Self {
        self.starting_stacks = amount;
        self
    }
    
    // Card control methods
    
    pub fn hole_cards(mut self, player: usize, cards: &str) -> Result<Self> {
        if player >= self.num_players {
            bail!("Player {} is out of range for {} players", player, self.num_players);
        }
        
        // Parse the card string (e.g., "AhAs")
        let card_strings: Vec<String> = cards.chars()
            .collect::<Vec<_>>()
            .chunks(2)
            .map(|chunk| chunk.iter().collect::<String>())
            .collect();
        
        if card_strings.len() != 2 {
            bail!("Expected exactly 2 hole cards, got {} from '{}'", card_strings.len(), cards);
        }
        
        let mut parsed_cards = Vec::new();
        for card_str in card_strings {
            let card = Card::parse(&card_str)
                .map_err(|_| anyhow!("Failed to parse card '{}'", card_str))?;
            parsed_cards.push(card);
        }
        
        // Ensure hole_cards vector is large enough
        while self.hole_cards.len() <= player {
            self.hole_cards.push(None);
        }
        
        self.hole_cards[player] = Some(parsed_cards);
        Ok(self)
    }
    
    pub fn flop_cards(mut self, cards: &str) -> Result<Self> {
        // Parse the flop cards (e.g., "ThTd9c")
        let card_strings: Vec<String> = cards.chars()
            .collect::<Vec<_>>()
            .chunks(2)
            .map(|chunk| chunk.iter().collect::<String>())
            .collect();
        
        if card_strings.len() != 3 {
            bail!("Expected exactly 3 flop cards, got {} from '{}'", card_strings.len(), cards);
        }
        
        let mut parsed_cards = Vec::new();
        for card_str in card_strings {
            let card = Card::parse(&card_str)
                .map_err(|_| anyhow!("Failed to parse card '{}'", card_str))?;
            parsed_cards.push(card);
        }
        
        self.flop_cards = Some(parsed_cards);
        Ok(self)
    }
    
    pub fn turn_card(mut self, card: &str) -> Result<Self> {
        let parsed_card = Card::parse(card)
            .map_err(|_| anyhow!("Failed to parse card '{}'", card))?;
        
        self.turn_card = Some(parsed_card);
        Ok(self)
    }
    
    pub fn river_card(mut self, card: &str) -> Result<Self> {
        let parsed_card = Card::parse(card)
            .map_err(|_| anyhow!("Failed to parse card '{}'", card))?;
        
        self.river_card = Some(parsed_card);
        Ok(self)
    }
    
    pub fn with_metrics<T: MetricsCollector + 'static>(mut self, collector: Arc<Mutex<T>>) -> Self {
        self.metrics_collector = Some(collector);
        self
    }
    
    pub fn build(self) -> Result<HulhScriptedGame> {
        // Validate configuration
        if self.num_players < 2 || self.num_players > 6 {
            bail!("Number of players must be between 2 and 6");
        }
        
        let button_position = self.button_position.unwrap_or(0);
        if button_position >= self.num_players {
            bail!("Button position {} is invalid for {} players", button_position, self.num_players);
        }
        
        // Validate hole cards - if any are specified, all must be specified
        let players_with_cards = (0..self.num_players)
            .filter(|&p| self.hole_cards.get(p).map_or(false, |c| c.is_some()))
            .count();
            
        if players_with_cards > 0 && players_with_cards < self.num_players {
            bail!("If hole cards are specified, they must be specified for all players. {} of {} players have cards specified", 
                  players_with_cards, self.num_players);
        }
        
        // Validate no duplicate cards
        let mut all_cards = HashSet::new();
        
        // Check hole cards
        for (i, hole_cards_opt) in self.hole_cards.iter().enumerate() {
            if let Some(cards) = hole_cards_opt {
                for card in cards {
                    if !all_cards.insert(*card) {
                        bail!("Duplicate card {} in player {}'s hole cards", card, i);
                    }
                }
            }
        }
        
        // Check flop cards
        if let Some(ref flop) = self.flop_cards {
            for card in flop {
                if !all_cards.insert(*card) {
                    bail!("Duplicate card {} in flop", card);
                }
            }
        }
        
        // Check turn card
        if let Some(card) = self.turn_card {
            if !all_cards.insert(card) {
                bail!("Duplicate card {} in turn", card);
            }
        }
        
        // Check river card
        if let Some(card) = self.river_card {
            if !all_cards.insert(card) {
                bail!("Duplicate card {} in river", card);
            }
        }
        
        // Create rigged deck if we have any preset cards
        let rigged_deck = if !all_cards.is_empty() {
            // Build the sequence of cards for the rigged deck
            let mut card_sequence = Vec::new();
            
            // Add hole cards in dealing order
            // In HULH, cards are dealt one at a time in rotation starting from SB
            let sb_player = if self.num_players == 2 {
                button_position
            } else {
                (button_position + 1) % self.num_players
            };
            
            // Add hole cards in dealing order (we've already validated all players have cards)
            let has_hole_cards = self.hole_cards.iter().any(|c| c.is_some());
            if has_hole_cards {
                for card_idx in 0..2 {
                    for player_offset in 0..self.num_players {
                        let player = (sb_player + player_offset) % self.num_players;
                        if let Some(Some(ref cards)) = self.hole_cards.get(player) {
                            if let Some(card) = cards.get(card_idx) {
                                card_sequence.push(card.to_string());
                            }
                        }
                    }
                }
            }
            
            // Add board cards
            if let Some(ref flop) = self.flop_cards {
                for card in flop {
                    card_sequence.push(card.to_string());
                }
            }
            
            if let Some(card) = self.turn_card {
                card_sequence.push(card.to_string());
            }
            
            if let Some(card) = self.river_card {
                card_sequence.push(card.to_string());
            }
            
            Some(Box::new(RiggedFastDeck::new(&card_sequence)?) as Box<dyn FastDeckTrait>)
        } else {
            None
        };
        
        // Create the game
        let mut settings = HulhSettings::default();
        settings.num_players = self.num_players;
        settings.small_blind = self.small_blind;
        settings.big_blind = self.big_blind;
        settings.starting_stack = self.starting_stacks;
        settings.vector_cards = false; // Important: Use deck mode for card control
        
        let game = HulhGame::new_with_settings(settings);
        
        Ok(HulhScriptedGame {
            game: Arc::new(game),
            state: None,
            button_position,
            hole_cards: self.hole_cards,
            flop_cards: self.flop_cards,
            turn_card: self.turn_card,
            river_card: self.river_card,
            rigged_deck,
            metrics_collector: self.metrics_collector,
            action_history: Vec::new(),
        })
    }
}

/// A scripted HULH game for testing
pub struct HulhScriptedGame {
    game: Arc<HulhGame>,
    state: Option<HulhState>,
    button_position: usize,
    hole_cards: Vec<Option<Vec<Card>>>,
    flop_cards: Option<Vec<Card>>,
    turn_card: Option<Card>,
    river_card: Option<Card>,
    rigged_deck: Option<Box<dyn FastDeckTrait>>,
    metrics_collector: Option<Arc<Mutex<dyn MetricsCollector>>>,
    action_history: Vec<(PlayerId, ConcreteAction)>,
}

impl fmt::Debug for HulhScriptedGame {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("HulhScriptedGame")
            .field("button_position", &self.button_position)
            .field("num_players", &self.game.num_players())
            .field("has_state", &self.state.is_some())
            .field("hole_cards", &self.hole_cards)
            .field("flop_cards", &self.flop_cards)
            .field("turn_card", &self.turn_card)
            .field("river_card", &self.river_card)
            .field("has_rigged_deck", &self.rigged_deck.is_some())
            .field("has_metrics_collector", &self.metrics_collector.is_some())
            .field("action_history_len", &self.action_history.len())
            .finish()
    }
}

impl HulhScriptedGame {
    pub fn new() -> HulhScriptedGameBuilder {
        HulhScriptedGameBuilder::new()
    }
    
    /// Initialize the game state
    fn init_state(&mut self) -> Result<()> {
        if self.state.is_some() {
            return Ok(());
        }
        
        // Set position context for the button
        set_position_context(Some(PositionMapping::new(self.button_position, self.game.num_players())));
        
        // Create initial state
        let mut rng = CfrRngPool::from_seed(42);
        let mut state = self.game.new_initial_state(&mut rng);
        
        // Clear position context
        clear_position_context();
        
        // If we have a rigged deck, replace the state's deck
        if let Some(rigged_deck) = self.rigged_deck.take() {
            state.deck = rigged_deck;
        }
        
        // Track hand start for metrics
        if let Some(ref collector) = self.metrics_collector {
            collector.lock().unwrap().start_hand(self.button_position);
        }
        
        self.state = Some(state);
        Ok(())
    }
    
    /// Get current state, initializing if needed
    pub fn get_state(&mut self) -> Result<&mut HulhState> {
        self.init_state()?;
        self.state.as_mut().ok_or_else(|| anyhow!("Failed to initialize state"))
    }
    
    // Action methods
    pub fn player_raises(&mut self, player: PlayerId, _amount: Chips) -> Result<()> {
        let state = self.get_state()?;
        
        if state.current_player() != player {
            bail!("Player {} cannot act out of turn (current player: {})", player, state.current_player());
        }
        
        // In HULH, raise is a fixed action
        let legal_actions = state.legal_actions();
        if !legal_actions.contains(&RAISE_ACTION) {
            bail!("Player {} cannot raise - action not legal", player);
        }
        
        self.apply_action(player, RAISE_ACTION)?;
        Ok(())
    }
    
    pub fn player_calls(&mut self, player: PlayerId) -> Result<()> {
        let state = self.get_state()?;
        
        if state.current_player() != player {
            bail!("Player {} cannot act out of turn", player);
        }
        
        let legal_actions = state.legal_actions();
        if !legal_actions.contains(&CALL_ACTION) {
            bail!("Player {} cannot call - action not legal", player);
        }
        
        self.apply_action(player, CALL_ACTION)?;
        Ok(())
    }
    
    pub fn player_checks(&mut self, player: PlayerId) -> Result<()> {
        let state = self.get_state()?;
        
        if state.current_player() != player {
            bail!("Player {} cannot act out of turn", player);
        }
        
        let legal_actions = state.legal_actions();
        if !legal_actions.contains(&CALL_ACTION) {
            bail!("Player {} cannot check - action not legal", player);
        }
        
        self.apply_action(player, CALL_ACTION)?;
        Ok(())
    }
    
    pub fn player_folds(&mut self, player: PlayerId) -> Result<()> {
        let state = self.get_state()?;
        
        if state.current_player() != player {
            bail!("Player {} cannot act out of turn", player);
        }
        
        self.apply_action(player, FOLD_ACTION)?;
        Ok(())
    }
    
    pub fn player_bets(&mut self, player: PlayerId, amount: Chips) -> Result<()> {
        // In HULH, a bet is just a raise when no one has bet yet
        self.player_raises(player, amount)
    }
    
    fn apply_action(&mut self, player: PlayerId, action: ConcreteAction) -> Result<()> {
        // Get betting context and round from state
        let (betting_context, round) = {
            let state = self.get_state()?;
            (state.get_betting_context(player, action), state.round() as u8)
        };
        
        // Track action for metrics with betting context
        if let Some(ref collector) = self.metrics_collector {
            let action_context = ActionContext {
                seat: player,
                round,
                action,
                amount: betting_context.pot_size as i32,
                facing_bet: betting_context.facing_bet,
                is_bb_option: betting_context.is_bb_option,
            };
            collector.lock().unwrap().track_action(action_context);
        }
        
        // Apply the action
        let state = self.get_state()?;
        state.apply_action(action)?;
        
        self.action_history.push((player, action));
        
        Ok(())
    }
    
    // Street advancement
    pub fn deal_flop(&mut self) -> Result<()> {
        // Deal cards through chance nodes until we're no longer at a chance node
        // This handles the flop dealing after preflop betting completes
        let initial_round = self.get_state()?.round();
        
        while self.get_state()?.is_chance_node() {
            let action = {
                let state = self.get_state()?;
                let actions = state.chance_outcomes();
                if !actions.is_empty() {
                    Some(actions[0].0)
                } else {
                    None
                }
            };
            
            if let Some(action) = action {
                let state = self.get_state()?;
                state.apply_action(action)?;
            } else {
                break;
            }
        }
        
        // Verify we've advanced from the initial round
        let final_round = self.get_state()?.round();
        if final_round == initial_round && initial_round == 0 {
            bail!("Failed to advance to flop - still in preflop");
        }
        
        Ok(())
    }
    
    pub fn deal_turn(&mut self) -> Result<()> {
        // Deal cards through chance nodes for the turn
        let initial_round = self.get_state()?.round();
        
        while self.get_state()?.is_chance_node() {
            let action = {
                let state = self.get_state()?;
                let actions = state.chance_outcomes();
                if !actions.is_empty() {
                    Some(actions[0].0)
                } else {
                    None
                }
            };
            
            if let Some(action) = action {
                let state = self.get_state()?;
                state.apply_action(action)?;
            } else {
                break;
            }
        }
        
        // Verify we've advanced appropriately
        let final_round = self.get_state()?.round();
        if final_round == initial_round && initial_round == 1 {
            bail!("Failed to advance to turn - still in flop");
        }
        
        Ok(())
    }
    
    pub fn deal_river(&mut self) -> Result<()> {
        // Deal cards through chance nodes for the river
        let initial_round = self.get_state()?.round();
        
        while self.get_state()?.is_chance_node() {
            let action = {
                let state = self.get_state()?;
                let actions = state.chance_outcomes();
                if !actions.is_empty() {
                    Some(actions[0].0)
                } else {
                    None
                }
            };
            
            if let Some(action) = action {
                let state = self.get_state()?;
                state.apply_action(action)?;
            } else {
                break;
            }
        }
        
        // Verify we've advanced appropriately
        let final_round = self.get_state()?.round();
        if final_round == initial_round && initial_round == 2 {
            bail!("Failed to advance to river - still in turn");
        }
        
        Ok(())
    }
    
    pub fn complete_hand(&mut self) -> Result<HandResult> {
        // Run to completion
        loop {
            let (is_terminal, is_chance, player) = {
                let state = self.get_state()?;
                (state.is_terminal(), state.is_chance_node(), state.current_player())
            };
            
            if is_terminal {
                break;
            }
            
            if is_chance {
                let action = {
                    let state = self.get_state()?;
                    let actions = state.chance_outcomes();
                    if !actions.is_empty() {
                        Some(actions[0].0)
                    } else {
                        None
                    }
                };
                
                if let Some(action) = action {
                    let state = self.get_state()?;
                    state.apply_action(action)?;
                }
            } else {
                // Make default action (check/call)
                let action = {
                    let state = self.get_state()?;
                    let legal = state.legal_actions();
                    if legal.contains(&CALL_ACTION) {
                        CALL_ACTION
                    } else {
                        legal[0]
                    }
                };
                
                self.apply_action(player, action)?;
            }
        }
        
        // Extract result
        let result = self.get_hand_result();
        
        // Finalize metrics
        if let Some(ref collector) = self.metrics_collector {
            let went_to_showdown = result.went_to_showdown.clone();
            let mut won_at_showdown = vec![false; self.num_players()];
            let mut won_hand = vec![false; self.num_players()];
            
            for &winner in &result.winners {
                if winner < self.num_players() {
                    won_hand[winner] = true;
                    if went_to_showdown[winner] {
                        won_at_showdown[winner] = true;
                    }
                }
            }
            
            // Pass both won_at_showdown and won_hand for proper WWSF tracking
            // For backwards compatibility, we'll update finalize_hand to use won_at_showdown for WWSF if no separate won_hand is tracked
            collector.lock().unwrap().finalize_hand(self.button_position, went_to_showdown, won_hand);
        }
        
        Ok(result)
    }
    
    // State queries
    pub fn num_players(&self) -> usize {
        self.game.num_players()
    }
    
    pub fn button_position(&self) -> usize {
        self.button_position
    }
    
    pub fn current_player(&mut self) -> Result<PlayerId> {
        let state = self.get_state()?;
        Ok(state.current_player())
    }
    
    pub fn pot_size(&mut self) -> Result<Chips> {
        let state = self.get_state()?;
        Ok(state.pot())
    }
    
    pub fn current_street(&mut self) -> Result<Street> {
        let state = self.get_state()?;
        let round = state.round();
        Ok(match round {
            0 => Street::Preflop,
            1 => Street::Flop,
            2 => Street::Turn,
            3 => Street::River,
            _ => bail!("Invalid round: {}", round),
        })
    }
    
    pub fn is_hand_complete(&mut self) -> Result<bool> {
        let state = self.get_state()?;
        Ok(state.is_terminal())
    }
    
    pub fn is_all_in(&mut self) -> Result<bool> {
        let _state = self.get_state()?;
        // Check if any player has 0 chips remaining
        // This is a simplified check - might need to look at state.stacks or similar
        Ok(false) // Placeholder
    }
    
    pub fn get_winners(&mut self) -> Result<Vec<PlayerId>> {
        let state = self.get_state()?;
        if !state.is_terminal() {
            bail!("Cannot determine winners - hand not complete");
        }
        
        // Get returns and find winners (highest return)
        let returns = state.returns();
        let max_return = returns.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        
        let winners: Vec<PlayerId> = returns.iter()
            .enumerate()
            .filter(|(_, &ret)| (ret - max_return).abs() < 1e-6) // Float comparison with epsilon
            .map(|(i, _)| i)
            .collect();
        
        Ok(winners)
    }
    
    pub fn get_board(&mut self) -> Result<String> {
        let state = self.get_state()?;
        let mut board = String::new();
        
        for i in 0..state.board_cards_len as usize {
            // Card's Display impl returns uppercase, convert to lowercase with proper casing
            let card_str = state.board_cards[i].to_string();
            if card_str.len() == 2 {
                // Convert rank to uppercase, suit to lowercase (e.g., "AS" -> "As")
                board.push(card_str.chars().nth(0).unwrap());
                board.push(card_str.chars().nth(1).unwrap().to_lowercase().next().unwrap());
            }
        }
        
        Ok(board)
    }
    
    pub fn get_hole_cards(&mut self, player: usize) -> Result<String> {
        let state = self.get_state()?;
        
        if player >= state.num_players() {
            bail!("Player {} is out of range", player);
        }
        
        let mut cards = String::new();
        
        // Access the public private_cards field
        for i in 0..state.config_num_hole_cards {
            if let Some(card) = state.private_cards[player][i] {
                // Card's Display impl returns uppercase, convert to lowercase with proper casing
                let card_str = card.to_string();
                if card_str.len() == 2 {
                    // Convert rank to uppercase, suit to lowercase (e.g., "AS" -> "As")
                    cards.push(card_str.chars().nth(0).unwrap());
                    cards.push(card_str.chars().nth(1).unwrap().to_lowercase().next().unwrap());
                }
            }
        }
        
        if cards.is_empty() {
            Ok("(not dealt)".to_string())
        } else {
            Ok(cards)
        }
    }
    
    pub fn get_hand_result(&mut self) -> HandResult {
        // Get all info from state in one go
        let (pot_size, went_to_showdown, winners) = {
            let state = self.get_state().unwrap();
            let pot = state.pot();
            let showdown = state.went_to_showdown();
            (pot, showdown, None)
        };
        
        // Get winners separately since it requires mutable self
        let winners = winners.unwrap_or_else(|| self.get_winners().unwrap_or_default());
        
        HandResult {
            winners,
            pot_size,
            went_to_showdown,
        }
    }
}

/// Street in a poker game
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Street {
    Preflop,
    Flop,
    Turn,
    River,
}

/// Action type for quick hand utility
#[derive(Debug, Clone)]
pub enum QuickAction {
    /// Player raises (amount is fixed in HULH)
    Raise(PlayerId),
    /// Player calls
    Call(PlayerId),
    /// Player checks
    Check(PlayerId), 
    /// Player folds
    Fold(PlayerId),
    /// Player bets (same as raise in HULH)
    Bet(PlayerId),
    /// Deal flop
    Flop,
    /// Deal turn
    Turn,
    /// Deal river
    River,
}

impl HulhScriptedGame {
    /// Create and play a hand in one line for quick testing
    /// 
    /// # Example
    /// ```ignore
    /// let result = HulhScriptedGame::quick_hand(
    ///     2,                                    // players
    ///     vec!["AhAs", "KdKc"],                // hole cards (optional)
    ///     Some("ThTd9c8s7h"),                  // full board (optional)
    ///     vec![
    ///         QuickAction::Raise(0),
    ///         QuickAction::Call(1),
    ///         QuickAction::Flop,
    ///         QuickAction::Check(1),
    ///         QuickAction::Bet(0),
    ///         QuickAction::Fold(1),
    ///     ]
    /// )?;
    /// ```
    pub fn quick_hand(
        players: usize,
        hole_cards: Vec<&str>,
        board: Option<&str>,
        actions: Vec<QuickAction>,
    ) -> Result<HandResult> {
        let mut builder = HulhScriptedGame::new().players(players);
        
        // Set hole cards if provided
        for (i, cards) in hole_cards.iter().enumerate() {
            builder = builder.hole_cards(i, cards)?;
        }
        
        // Parse board if provided
        if let Some(board_str) = board {
            let board_len = board_str.len();
            if board_len >= 6 {
                // Extract flop (first 6 chars)
                builder = builder.flop_cards(&board_str[0..6])?;
            }
            if board_len >= 8 {
                // Extract turn (chars 6-7)
                builder = builder.turn_card(&board_str[6..8])?;
            }
            if board_len >= 10 {
                // Extract river (chars 8-9)
                builder = builder.river_card(&board_str[8..10])?;
            }
        }
        
        let mut game = builder.build()?;
        
        // Deal hole cards if not already dealt
        while game.get_state()?.is_chance_node() {
            let chance_action = game.get_state()?.chance_outcomes()[0].0;
            game.get_state()?.apply_action(chance_action)?;
        }
        
        // Execute actions
        for action in actions {
            match action {
                QuickAction::Raise(player) => game.player_raises(player, 0)?,
                QuickAction::Call(player) => game.player_calls(player)?,
                QuickAction::Check(player) => game.player_checks(player)?,
                QuickAction::Fold(player) => game.player_folds(player)?,
                QuickAction::Bet(player) => game.player_bets(player, 0)?,
                QuickAction::Flop => game.deal_flop()?,
                QuickAction::Turn => game.deal_turn()?,
                QuickAction::River => game.deal_river()?,
            }
        }
        
        game.complete_hand()
    }
    
    /// Run a sequence of hands with button rotation for position testing
    /// 
    /// # Example
    /// ```ignore
    /// let results = HulhScriptedGame::run_hand_sequence(
    ///     3,  // players
    ///     vec![
    ///         // Hand 1
    ///         vec![QuickAction::Raise(0), QuickAction::Fold(1), QuickAction::Fold(2)],
    ///         // Hand 2  
    ///         vec![QuickAction::Call(1), QuickAction::Call(2), QuickAction::Check(0)],
    ///     ],
    ///     true,  // rotate button
    /// )?;
    /// ```
    pub fn run_hand_sequence(
        players: usize,
        hand_actions: Vec<Vec<QuickAction>>,
        rotate_button: bool,
    ) -> Result<Vec<HandResult>> {
        let mut results = Vec::new();
        let mut button_position = 0;
        let num_hands = hand_actions.len();
        
        for (hand_idx, actions) in hand_actions.into_iter().enumerate() {
            let mut game = HulhScriptedGame::new()
                .players(players)
                .button_position(button_position)
                .build()?;
            
            // Deal hole cards before actions
            while game.get_state()?.is_chance_node() {
                let chance_action = game.get_state()?.chance_outcomes()[0].0;
                game.get_state()?.apply_action(chance_action)?;
            }
            
            // Execute actions for this hand
            for action in actions {
                match action {
                    QuickAction::Raise(player) => game.player_raises(player, 0)?,
                    QuickAction::Call(player) => game.player_calls(player)?,
                    QuickAction::Check(player) => game.player_checks(player)?,
                    QuickAction::Fold(player) => game.player_folds(player)?,
                    QuickAction::Bet(player) => game.player_bets(player, 0)?,
                    QuickAction::Flop => game.deal_flop()?,
                    QuickAction::Turn => game.deal_turn()?,
                    QuickAction::River => game.deal_river()?,
                }
            }
            
            let result = game.complete_hand()?;
            results.push(result);
            
            // Rotate button for next hand if requested
            if rotate_button && hand_idx < num_hands - 1 {
                button_position = (button_position + 1) % players;
            }
        }
        
        Ok(results)
    }
    
    /// Run a sequence of hands with metrics collection
    pub fn run_hand_sequence_with_metrics<T: MetricsCollector + 'static>(
        players: usize,
        hand_actions: Vec<Vec<QuickAction>>,
        rotate_button: bool,
        metrics_collector: Arc<Mutex<T>>,
    ) -> Result<(Vec<HandResult>, Arc<Mutex<T>>)> {
        let mut results = Vec::new();
        let mut button_position = 0;
        let num_hands = hand_actions.len();
        
        for (hand_idx, actions) in hand_actions.into_iter().enumerate() {
            let mut game = HulhScriptedGame::new()
                .players(players)
                .button_position(button_position)
                .with_metrics(metrics_collector.clone())
                .build()?;
            
            // Deal hole cards before actions
            while game.get_state()?.is_chance_node() {
                let chance_action = game.get_state()?.chance_outcomes()[0].0;
                game.get_state()?.apply_action(chance_action)?;
            }
            
            // Execute actions for this hand
            for action in actions {
                match action {
                    QuickAction::Raise(player) => game.player_raises(player, 0)?,
                    QuickAction::Call(player) => game.player_calls(player)?,
                    QuickAction::Check(player) => game.player_checks(player)?,
                    QuickAction::Fold(player) => game.player_folds(player)?,
                    QuickAction::Bet(player) => game.player_bets(player, 0)?,
                    QuickAction::Flop => game.deal_flop()?,
                    QuickAction::Turn => game.deal_turn()?,
                    QuickAction::River => game.deal_river()?,
                }
            }
            
            let result = game.complete_hand()?;
            results.push(result);
            
            // Rotate button for next hand if requested
            if rotate_button && hand_idx < num_hands - 1 {
                button_position = (button_position + 1) % players;
            }
        }
        
        Ok((results, metrics_collector))
    }
}
```

crates/games/src/hulh/settings.rs:
```
//! Defines the HulhSettings struct for HULH game configuration.

use crate::Chips; // Use Chips from crate root
use engine::{
	settings::GameSettings,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// --- Game Rules Enum ---

/// Specifies the primary game rules variant.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum HulhGameRules {
	Holdem,
}

// --- Raise Rule Type Enum ---
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash, Default)]
pub enum RaiseRuleType {
	#[default]
	FixedAmount, // Raises are by a fixed amount specified for the round
	DoublePreviousBetOrRaise, // Raises must be double the last bet or raise increment
	MatchPreviousBetOrRaise, // Raises must match the monetary amount of the last bet or raise increment
}

/// Creates HulhSettings for Short-Deck Hold'em (36-card deck, otherwise
/// standard Hold'em rules: 2 hole cards, 4 betting rounds, fixed-limit).
pub fn new_shortdeck_holdem_settings(vector_cards: bool) -> HulhSettings {
	let big_blind_default: Chips = 2;
	HulhSettings {
		name: "ShortDeckHoldem".to_string(),
		num_players: 2,
		num_rounds: 4,
		max_raises: vec![3, 4, 4, 4],
		num_hole_cards: 2,
		board_cards_per_round: vec![0, 3, 1, 1],
		small_blind: 1,
		big_blind: big_blind_default,
		fixed_raise_amounts: vec![
			big_blind_default,
			big_blind_default,
			big_blind_default * 2,
			big_blind_default * 2,
		],
		opening_bet_sizes: vec![
			vec![big_blind_default],     // Pre-flop
			vec![big_blind_default],     // Flop
			vec![big_blind_default * 2], // Turn
			vec![big_blind_default * 2], // River
		],
		raise_rule: RaiseRuleType::FixedAmount,
		starting_stack: 100,
		ante: 0,
		deck_type: DeckType::ShortDeck36,
		vector_cards,
		game_rules: HulhGameRules::Holdem,
	}
}

// --- Deck Type Enum ---

/// Specifies the type of deck to use for the HULH game.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum DeckType {
	Standard52,
	ShortDeck36, // 36-card short deck (6-A) for Short-Deck Hold'em
}

// --- HulhSettings Struct ---

/// Configuration settings for a HULH game.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)] // Eq removed due to f64 and Vec<Vec<Chips>> potentially
pub struct HulhSettings {
	pub num_players: usize,
	pub name: String,
	pub num_rounds: usize,
	pub max_raises: Vec<usize>, // Max raises per round
	pub num_hole_cards: usize,
	pub board_cards_per_round: Vec<usize>, // e.g., [0, 3, 1, 1] for Pre, Flop, Turn, River
	pub small_blind: Chips,
	pub big_blind: Chips,
	// pub raise_sizes: Vec<Chips>, // Removed
	pub fixed_raise_amounts: Vec<Chips>, // For FixedAmount rule, stores bet/raise size per round
	pub opening_bet_sizes: Vec<Vec<Chips>>, // Allowed opening bet sizes per round
	pub raise_rule: RaiseRuleType,       // Defines how raise amounts are determined
	pub starting_stack: Chips,
	pub ante: Chips,         // Ante amount, applied per player per hand/round if > 0
	pub deck_type: DeckType, // Explicitly define the deck type
	/// If true, cards for the entire hand (hole and board) are determined at the
	/// start of the game and stored. These cards will not be re-sampled,
	/// ensuring a fixed sequence even through undo/apply action cycles.
	/// For more dynamic external control over card sequences (e.g., for specific
	/// testing scenarios beyond initial pre-assignment), a rigged `FastDeck`
	/// implementation should be used in conjunction with `vector_cards = false`.
	pub vector_cards: bool,
	/// Specifies the primary game rules variant (Holdem or Leduc).
	pub game_rules: HulhGameRules,
}

impl Default for HulhSettings {
	fn default() -> Self {
		// Default settings assume 2 players for HU values, 3+ for Multi values.
		// HU Preflop: P0 (Button/SB)
		// HU Postflop: P1 (BB)
		// Multi Preflop: P2 (UTG in 3p)
		// Multi Postflop: P0 (SB in 3p)
		let big_blind_default: Chips = 2;
		HulhSettings {
			name: "HULH".to_string(),
			num_players: 2,
			num_rounds: 4,
			max_raises: vec![3, 4, 4, 4],
			num_hole_cards: 2,
			board_cards_per_round: vec![0, 3, 1, 1],
			small_blind: 1,
			big_blind: big_blind_default,
			fixed_raise_amounts: vec![
				big_blind_default,
				big_blind_default,
				big_blind_default * 2,
				big_blind_default * 2,
			], // e.g., [2, 2, 4, 4]
			opening_bet_sizes: vec![
				vec![big_blind_default],     // Preflop
				vec![big_blind_default],     // Flop
				vec![big_blind_default * 2], // Turn
				vec![big_blind_default * 2], // River
			],
			raise_rule: RaiseRuleType::FixedAmount,
			starting_stack: 100,
			ante: 0,
			deck_type: DeckType::Standard52,
			vector_cards: false, // Default to false
			game_rules: HulhGameRules::Holdem,
		}
	}
}

impl HulhSettings {
	/// Calculate first to act preflop based on dealer button
	pub fn first_to_act_preflop(&self, dealer_btn: engine::types::PlayerId) -> engine::types::PlayerId {
		crate::hulh::constants::first_to_act_preflop(dealer_btn, self.num_players)
	}
	
	/// Calculate first to act postflop based on dealer button  
	pub fn first_to_act_postflop(&self, dealer_btn: engine::types::PlayerId) -> engine::types::PlayerId {
		crate::hulh::constants::first_to_act_postflop(dealer_btn, self.num_players)
	}
	
	/// Calculate small blind position based on dealer button
	pub fn small_blind(&self, dealer_btn: engine::types::PlayerId) -> engine::types::PlayerId {
		crate::hulh::constants::small_blind(dealer_btn, self.num_players)
	}
	
	/// Calculate big blind position based on dealer button
	pub fn big_blind(&self, dealer_btn: engine::types::PlayerId) -> engine::types::PlayerId {
		crate::hulh::constants::big_blind(dealer_btn, self.num_players)
	}
}

impl GameSettings for HulhSettings {
	fn to_key_value(&self) -> HashMap<String, String> {
		let mut map = HashMap::new();
		map.insert("players".to_string(), self.num_players.to_string());
		map.insert("num_rounds".to_string(), self.num_rounds.to_string());
		map.insert(
			"max_raises".to_string(),
			self.max_raises
				.iter()
				.map(|x| x.to_string())
				.collect::<Vec<String>>()
				.join(","),
		);
		map.insert(
			"num_hole_cards".to_string(),
			self.num_hole_cards.to_string(),
		);
		map.insert(
			"board_cards_per_round".to_string(),
			self.board_cards_per_round
				.iter()
				.map(|x| x.to_string())
				.collect::<Vec<String>>()
				.join(","),
		);
		map.insert("small_blind".to_string(), self.small_blind.to_string());
		map.insert("big_blind".to_string(), self.big_blind.to_string());
		map.insert(
			"fixed_raise_amounts".to_string(),
			self.fixed_raise_amounts
				.iter()
				.map(|x| x.to_string())
				.collect::<Vec<String>>()
				.join(","),
		);
		map.insert(
			"opening_bet_sizes".to_string(),
			self.opening_bet_sizes
				.iter()
				.map(|round_sizes| {
					round_sizes
						.iter()
						.map(|s| s.to_string())
						.collect::<Vec<String>>()
						.join("-")
				})
				.collect::<Vec<String>>()
				.join(";"),
		);
		map.insert("raise_rule".to_string(), format!("{:?}", self.raise_rule));
		map.insert(
			"starting_stack".to_string(),
			self.starting_stack.to_string(),
		);
		map.insert("ante".to_string(), self.ante.to_string());
		map.insert("deck_type".to_string(), format!("{:?}", self.deck_type));
		map.insert(
			"use_pre_assigned_hole_cards".to_string(),
			self.vector_cards.to_string(),
		);
		map.insert("game_rules".to_string(), format!("{:?}", self.game_rules));
		map
	}

	fn get_game_name(&self) -> String {
		self.name.clone()
	}
}


```

crates/games/src/hulh/state/betting.rs:
```
#![allow(unused)]
//! Logic for handling player betting actions in HULH.

use super::core::{HulhState, Pot};
use crate::hulh::action::HulhMove; // Keep HulhMove
use crate::hulh::{
	constants::*,
	settings::RaiseRuleType,  // Import RaiseRuleType
	state::{round, showdown}, // Import sibling modules
	undo::{PreResolveState, PreRoundState, UndoRecord},
};
use crate::Chips; // Use Chips from crate root
use engine::{
	error::{GameError, GameResult},
	types::{ConcreteAction, PlayerId, CHANCE_PLAYER_ID, TERMINAL_PLAYER_ID}, // Keep engine types
};
use log;
use smallvec::SmallVec;

/// Checks if the player is facing a bet (i.e., needs to contribute more chips to match the current stake).
#[inline]
pub(crate) fn facing_bet(state: &HulhState, player: PlayerId) -> bool {
	assert!(player < state.num_players);
	let result = state.ante[player] < state.stakes;
	log::trace!("[facing_bet] P{}: ante[{}]={} < stakes={} = {}", 
		player, player, state.ante[player], state.stakes, result);
	result
}

/// Checks if the player has enough chips to make a full raise.
#[inline]
pub(crate) fn player_can_raise(state: &HulhState, p: PlayerId) -> bool {
	assert!(p < state.num_players);
	if state.all_in[p] {
		return false;
	}

	// Determine the required raise increment based on the game's raise rule.
	let required_raise_increment: Chips = match state.config_raise_rule {
		RaiseRuleType::FixedAmount => {
			// Ensure the round index is valid for config_fixed_raise_amounts
			if state.round >= state.config_fixed_raise_amounts.len() {
				log::error!(
                    "player_can_raise: Round index {} out of bounds for config_fixed_raise_amounts (len {}). Defaulting to 0.",
                    state.round, state.config_fixed_raise_amounts.len()
                );
				return false; // Or handle as an error, cannot determine raise amount
			}
			state.config_fixed_raise_amounts[state.round]
		}
		RaiseRuleType::DoublePreviousBetOrRaise | RaiseRuleType::MatchPreviousBetOrRaise => {
			// If no bet/raise has occurred yet to double/match (e.g. only blinds posted, or ante-only game pre-open),
			// a "Raise" action is not possible. An "OpenBetX" should be used.
			if state.last_bet_or_raise_increment == 0 {
				log::trace!("[player_can_raise P{}] {:?}: last_bet_or_raise_increment is 0, cannot Raise.", p, state.config_raise_rule); // Perf: Low impact trace
				return false;
			}
			if state.config_raise_rule == RaiseRuleType::DoublePreviousBetOrRaise {
				state.last_bet_or_raise_increment * 2
			} else {
				// MatchPreviousBetOrRaise
				state.last_bet_or_raise_increment
			}
		}
	};

	// If the calculated increment is 0 (e.g. fixed amount for round is 0, or last_bet_or_raise_increment was 0 and somehow passed the check),
	// a raise is not meaningful.
	if required_raise_increment == 0 {
		log::trace!("[player_can_raise P{}] Required raise increment is 0, cannot Raise.", p); // Perf: Low impact trace
		return false;
	}

	// Chips the player must first commit to match the current stake.
	let to_call = state.stakes.saturating_sub(state.ante[p]); // Use saturating_sub for safety

	// A *legal* raise requires enough chips for the call *plus* the
	// minimum raise increment as specified for the current betting round.
	match to_call.checked_add(required_raise_increment) {
		Some(required_total_for_raise) => state.stacks[p] >= required_total_for_raise,
		None => false, // Overflow means player cannot afford
	}
}

/// True iff the fixed-limit raise-cap has been reached for the current round.
///
/// **ENGINE DEVIATION from `rules.md` / TDA:**
/// Standard LHE rules (and TDA Rule 42) typically lift the raise cap when play
/// becomes heads-up. However, for practical AI training purposes (to prevent
/// agents getting stuck in infinite raise loops), this engine *always* enforces
/// the cap defined in `config_max_raises`, regardless of the number of players.
#[inline]
pub(crate) fn raise_cap_reached(state: &HulhState) -> bool {
	// Ensure round index is valid for config_max_raises
	if state.round >= state.config_max_raises.len() {
		log::error!(
            "raise_cap_reached: Round index {} out of bounds for config_max_raises (len {}). Assuming cap not reached.",
            state.round, state.config_max_raises.len()
        );
		return false; // Or handle as an error
	}
	let result = state.num_raises >= state.config_max_raises[state.round];
	log::trace!("[raise_cap_reached] Round {}: num_raises={} >= max_raises={} = {}", 
		state.round, state.num_raises, state.config_max_raises[state.round], result);
	result
}

/// Checks if the player has any chips left to call or check.
#[inline]
pub(crate) fn player_can_call(state: &HulhState, p: PlayerId) -> bool {
	assert!(p < state.num_players);
	// A player with exactly 0 chips must still be able to declare a
	// zero‑chip CALL (treated as "check" or as going all‑in for the
	// remainder).  Rely on `contribute()` to mark the player all‑in when
	// appropriate.
	let result = !state.all_in[p];
	log::trace!("[player_can_call] P{}: all_in[{}]={}, can_call={}", 
		p, p, state.all_in[p], result);
	result
}

/// Adds `amount` from `player` to the pot and updates contributions.
/// Caps contribution by stack and marks player all-in if necessary.
fn contribute(state: &mut HulhState, player: PlayerId, mut amount: Chips) {
	assert!(player < state.num_players);

	// if player == 0 { // Specific debug for P0 in the failing test
	// eprintln!("[CONTRIBUTE_P0_ENTRY] P0 trying to contribute amount={}. state.all_in[0]={}, state.stacks[0]={}, state.total_contribution[0]={}",
	// amount, state.all_in[0], state.stacks[0], state.total_contribution[0]);
	// }

	if amount == 0 && !state.all_in[player] {
		// Allow 0 amount contribution if it's a check essentially, but don't process if already all_in and amount is 0
		// if player == 0 && state.num_players == 3 { eprintln!("[CONTRIBUTE_P0_DEBUG_3P] amount is 0 and not all_in. Returning."); }
		return;
	}
	if state.all_in[player] && amount > 0 {
		// Cannot contribute more if already all-in
		// Use eprintln for critical debug path, especially for P0 in 3-player game
		// if player == 0 && state.num_players == 3 {
		// eprintln!("[CONTRIBUTE_P0_GUARD_3P] P0 IS ALL_IN (all_in[0]={}), amount={} > 0. IGNORING. Current TC[0]={}", state.all_in[0], amount, state.total_contribution[0]);
		// } else {
		log::warn!(
			"[contribute P{}] Attempted to contribute {} chips while already all-in. Ignoring.",
			player,
			amount
		);
		// }
		return; // This should prevent total_contribution update
	}

	// Cap amount by player's stack
	if amount >= state.stacks[player] {
		amount = state.stacks[player];
		state.all_in[player] = true; // Mark all-in if contributing full remaining stack
	}

	state.stacks[player] = state.stacks[player].saturating_sub(amount);
	state.ante[player] += amount;
	state.total_contribution[player] += amount; // THIS IS THE LINE THAT INCREMENTS TOTAL CONTRIBUTION
	state.pot += amount;

	// if player == 0 && state.num_players == 3 { // Specific debug for P0 in 3-player game
	// eprintln!("[CONTRIBUTE_P0_AFTER_UPDATE_3P] P0 contributed amount={}. New state.total_contribution[0]={}",
	// amount, state.total_contribution[0]);
	// }

	// If player is not yet marked all_in (e.g. contributed less than full stack)
	// but their remaining stack is less than a minimum meaningful wager, mark them all-in.
	if !state.all_in[player] {
		let min_future_wager = match state.config_raise_rule {
			RaiseRuleType::FixedAmount => {
				if state.round < state.config_fixed_raise_amounts.len() {
					state.config_fixed_raise_amounts[state.round]
				} else {
					log::warn!("contribute: Round index {} out of bounds for config_fixed_raise_amounts. Using 1 as min_future_wager.", state.round);
					1
				}
			}
			RaiseRuleType::DoublePreviousBetOrRaise | RaiseRuleType::MatchPreviousBetOrRaise => {
				if state.last_bet_or_raise_increment > 0 {
					if state.config_raise_rule == RaiseRuleType::DoublePreviousBetOrRaise {
						state.last_bet_or_raise_increment * 2
					} else {
						// MatchPreviousBetOrRaise
						state.last_bet_or_raise_increment
					}
				} else if state.round < state.config_opening_bet_sizes.len()
					&& !state.config_opening_bet_sizes[state.round].is_empty()
				{
					*state.config_opening_bet_sizes[state.round]
						.iter()
						.min()
						.unwrap_or(&1)
				} else {
					1
				}
			}
		};

		if state.stacks[player] < min_future_wager && min_future_wager > 0 {
			// log::debug!("[contribute P{}] Stack {} < min_future_wager {}. Marking all_in.", player, state.stacks[player], min_future_wager); // Perf: Low impact debug
			state.all_in[player] = true;
		}
	}
}

/// Handles the Fold action. Returns true if the player was folded.
fn apply_fold_action(state: &mut HulhState, player: PlayerId, mv: HulhMove) -> GameResult<bool> {
	if !facing_bet(state, player) {
		log::warn!(
			"[APPLY_BET FOLD P{}] Fold attempted when not facing a bet. Stakes={}, Ante={}",
			player,
			state.stakes,
			state.ante[player]
		);
		return Err(GameError::InvalidAction { action: mv.into() });
	}
	state.folded[player] = true;
	state.remaining_players -= 1;
	Ok(true)
}

/// Handles the Call action (unified call/check).
fn apply_call_action(state: &mut HulhState, player: PlayerId, mv: HulhMove) -> GameResult<()> {
    if facing_bet(state, player) {
        // Traditional call - match the current bet
        let amount_to_call = state.stakes.saturating_sub(state.ante[player]);
        contribute(state, player, amount_to_call);
    } else {
        // Not facing bet - this is a check (call 0)
        // Special case: track BB check preflop
        if player == state.bb_player() && state.round == 0 && state.num_raises == 0 {
            state.bb_checked_preflop = true;
        }
        // No chips to contribute when checking
    }
    Ok(())
}

// OpenBet actions removed - no longer needed

/// Handles the Raise action.
fn apply_raise_action(state: &mut HulhState, player: PlayerId, mv: HulhMove) -> GameResult<()> {
	if raise_cap_reached(state) {
		log::warn!(
			"[APPLY_BET RAISE P{}] Raise attempted but cap reached ({} raises of max {}).",
			player,
			state.num_raises,
			state.config_max_raises[state.round]
		);
		return Err(GameError::InvalidAction { action: mv.into() });
	}
	if !player_can_raise(state, player) {
		log::warn!("[APPLY_BET RAISE P{}] player_can_raise is false. Stakes={}, Ante={}, LastInc={}, Stack={}",
            player, state.stakes, state.ante[player], state.last_bet_or_raise_increment, state.stacks[player]);
		return Err(GameError::InvalidAction { action: mv.into() });
	}

	let amount_to_call = state.stakes.saturating_sub(state.ante[player]);
	let raise_increment: Chips = match state.config_raise_rule {
		RaiseRuleType::FixedAmount => state.config_fixed_raise_amounts[state.round],
		RaiseRuleType::DoublePreviousBetOrRaise | RaiseRuleType::MatchPreviousBetOrRaise => {
			if state.last_bet_or_raise_increment == 0 {
				log::error!(
					"[APPLY_BET RAISE P{}] {:?} rule but last_bet_or_raise_increment is 0.",
					player,
					state.config_raise_rule
				);
				return Err(GameError::LogicError(format!(
					"{:?} with no prior increment.",
					state.config_raise_rule
				)));
			}
			if state.config_raise_rule == RaiseRuleType::DoublePreviousBetOrRaise {
				state.last_bet_or_raise_increment * 2
			} else {
				// MatchPreviousBetOrRaise
				state.last_bet_or_raise_increment
			}
		}
	};

	contribute(state, player, amount_to_call + raise_increment);

	state.stakes += raise_increment;
	state.num_raises += 1;
	state.last_raiser = Some(player);
	state.last_bet_or_raise_increment = raise_increment;
	state.saw_forward_motion = true;
	Ok(())
}

/// Finalizes the betting action, updates history, transitions state if needed, and sets the next player.
/// Returns captured pre-transition states for undo.
fn complete_action_and_transition(
	state: &mut HulhState,
	player: PlayerId, // The player who just acted
	mv: HulhMove,
) -> GameResult<(Option<PreRoundState>, Option<PreResolveState>)> {
	let concrete_action = mv.into();
	state.sequence_append_move(concrete_action);
	state.action_history.push((player, concrete_action));

	let mut round_transition_state = None;
	let mut resolve_transition_state = None;

	if state.remaining_players <= 1 {
		// Perf: Removed for performance. This log involves formatting and was identified as part of a hot path.
		// log::debug!("[APPLY_BET_TRANSITION P{}] Hand ends: {} players remain.", player, state.remaining_players);
		let player_before_terminal = state.current_player; // This is `player`
		resolve_transition_state = Some(PreResolveState {
			winner: state.winner,
			evaluated_hands: state.evaluated_hands,
			_player_before_terminal: player_before_terminal,
		});
		showdown::resolve_showdown(state); // Sets current_player to TERMINAL_PLAYER_ID
	} else if round::is_betting_round_over(state) {
		// log::debug!("[APPLY_BET_TRANSITION P{}] Betting round over.", player); // Perf: Simple log, low impact
		if state.round == state.config_num_rounds - 1 {
			// log::debug!("[APPLY_BET_TRANSITION P{}] Final round. Resolving showdown.", player); // Perf: Simple log, low impact
			let player_before_terminal = state.current_player; // This is `player`
			resolve_transition_state = Some(PreResolveState {
				winner: state.winner,
				evaluated_hands: state.evaluated_hands,
				_player_before_terminal: player_before_terminal,
			});
			showdown::resolve_showdown(state); // Sets current_player to TERMINAL_PLAYER_ID
		} else {
			// log::debug!("[APPLY_BET_TRANSITION P{}] Not final round. Starting next round (dealing).", player); // Perf: Simple log, low impact
			let player_before_deal = state.current_player; // This is `player`
			round_transition_state = Some(PreRoundState {
				round: state.round,
				_num_raises: state.num_raises,
				_stakes: state.stakes,
				ante: state.ante,
				_last_raiser: state.last_raiser,
				_player_before_deal: player_before_deal,
				cards_dealt_this_round: state.cards_dealt_this_round,
				_last_bet_or_raise_increment: state.last_bet_or_raise_increment,
			});
			round::start_next_round(state); // Sets current_player to CHANCE_PLAYER_ID
		}
	} else {
		// No transition, just set the next betting player
		state.current_player = round::next_betting_player(state, player);
	}
	// If a transition occurred, state.current_player was already set by resolve_showdown or start_next_round.
	// If no transition, it's set by next_betting_player.

	Ok((round_transition_state, resolve_transition_state))
}

/// Applies a player's betting action (Fold, Call, Raise, OpenBetX).
pub(crate) fn apply_bet(state: &mut HulhState, player: PlayerId, mv: HulhMove) -> GameResult<()> {
	// Perf: This log involves many arguments and formatting, can be costly. Commented out.
	// log::debug!("[APPLY_BET_ENTRY] P{} attempts {:?}. Round={}, PlayerCurrent={}, NumRaises={}, Stakes={}, LastBetInc={}",
	//     player, mv, state.round, state.current_player, state.num_raises, state.stakes, state.last_bet_or_raise_increment);

	if player != state.current_player {
		log::error!(
			"[APPLY_BET] Out of turn action by P{} (current is P{}). Move: {:?}",
			player,
			state.current_player,
			mv
		);
		return Err(GameError::InvalidAction { action: mv.into() });
	}

	// Store initial pre-bet state for undo
	let undo_prev_stakes = state.stakes;
	let undo_prev_pot = state.pot;
	let undo_prev_ante = state.ante[player];
	let undo_prev_total_contribution = state.total_contribution[player];
	let undo_prev_num_raises = state.num_raises;
	let undo_prev_last_raiser = state.last_raiser;
	let undo_prev_bb_checked_preflop = state.bb_checked_preflop;
	let undo_prev_player = state.current_player; // This is `player`
	let undo_prev_saw_forward_motion = state.saw_forward_motion;
	let undo_prev_last_bet_or_raise_increment = state.last_bet_or_raise_increment;

	let mut was_folded = false;

	match mv {
		HulhMove::Fold => {
			was_folded = apply_fold_action(state, player, mv)?;
		}
		HulhMove::Call => {
			apply_call_action(state, player, mv)?;
		}
		HulhMove::Raise => {
			apply_raise_action(state, player, mv)?;
		}
	}

	let (round_transition_state, resolve_transition_state) =
		complete_action_and_transition(state, player, mv)?;

	state.undo_stack.push(UndoRecord::Bet {
		move_type: mv,
		player, // The player who acted
		prev_stakes: undo_prev_stakes,
		prev_pot: undo_prev_pot,
		prev_ante: undo_prev_ante,
		prev_total_contribution: undo_prev_total_contribution,
		prev_num_raises: undo_prev_num_raises,
		prev_last_raiser: undo_prev_last_raiser,
		prev_bb_checked_preflop: undo_prev_bb_checked_preflop,
		prev_saw_forward_motion: undo_prev_saw_forward_motion,
		was_folded,
		prev_player: undo_prev_player, // Player whose turn it was before this action
		round_transition_state,
		resolve_transition_state,
		prev_last_bet_or_raise_increment: undo_prev_last_bet_or_raise_increment,
	});

	// Perf: This log involves many arguments and formatting, can be costly. Commented out.
	// log::debug!("[APPLY_BET_EXIT] P{} action {:?} applied. Next player: P{}. Stakes={}, Pot={}, NumRaises={}, LastBetInc={}",
	//     player, mv, state.current_player, state.stakes, state.pot, state.num_raises, state.last_bet_or_raise_increment);

	Ok(())
}

/// Undoes a player's betting action.
#[allow(clippy::too_many_arguments)]
pub(crate) fn undo_bet(
	state: &mut HulhState,
	move_type: HulhMove,
	player: PlayerId, // Player who acted
	prev_stakes: Chips,
	prev_pot: Chips,
	prev_ante_player: Chips, // Player's specific ante before action
	prev_total_contribution_player: Chips, // Player's specific total contribution before action
	prev_num_raises: usize,
	prev_last_raiser: Option<PlayerId>,
	prev_bb_checked_preflop: bool,
	prev_saw_forward_motion: bool,
	was_folded: bool,
	prev_player_turn: PlayerId, // Player whose turn it was
	round_transition_state: Option<PreRoundState>,
	resolve_transition_state: Option<PreResolveState>,
	prev_last_bet_or_raise_increment: Chips, // Added for undo
) {
	let player_who_acted = player; // Clarify variable name

	// 1. Revert transitions first (if any)
	if let Some(ref pre_resolve) = resolve_transition_state {
		// log::trace!("[UNDO_BET_RESOLVE] Restoring pre_resolve. Winner: {:?}, PreResolve.evaluated_hands: P0={:?}, P1={:?}", pre_resolve.winner, pre_resolve.evaluated_hands.first().copied().flatten(), pre_resolve.evaluated_hands.get(1).copied().flatten());
		state.winner = pre_resolve.winner;
		// --- MODIFIED: Conditional restore of evaluated_hands ---
		if !state.config_vector_cards {
			// If not using vector_cards, always restore evaluated_hands from pre_resolve state.
			// This is because card sequences can change, making prior evaluations irrelevant.
			state.evaluated_hands = pre_resolve.evaluated_hands;
			// log::trace!("[UNDO_BET_RESOLVE] config_vector_cards=false. Restored evaluated_hands from pre_resolve. Current state.evaluated_hands: P0={:?}, P1={:?}", state.evaluated_hands.first().copied().flatten(), state.evaluated_hands.get(1).copied().flatten());
		} else {
			// If using vector_cards, DO NOT restore evaluated_hands from pre_resolve.
			// Instead, preserve the state.evaluated_hands that was set by the resolve_showdown
			// call that is currently being undone. This allows caching across different betting paths
			// that lead to the same (fixed) card showdown.
			// log::trace!("[UNDO_BET_RESOLVE] config_vector_cards=true. SKIPPED restoring evaluated_hands from pre_resolve. Current state.evaluated_hands (PRESERVED): P0={:?}, P1={:?}", state.evaluated_hands.first().copied().flatten(), state.evaluated_hands.get(1).copied().flatten());
		}
		// current_player is restored later to prev_player_turn
	} else if let Some(ref pre_round) = round_transition_state {
		state.round = pre_round.round;
		// num_raises, stakes, last_raiser, last_bet_or_raise_increment are restored below from direct prev_ values
		state.ante = pre_round.ante; // This restores the whole array if that's what was saved
		state.cards_dealt_this_round = pre_round.cards_dealt_this_round;
		// current_player is restored later
	}

	// 2. Restore core betting state fields to their values *before* this specific action
	state.stakes = prev_stakes;
	state.pot = prev_pot;
	state.num_raises = prev_num_raises;
	state.last_raiser = prev_last_raiser;
	state.bb_checked_preflop = prev_bb_checked_preflop;
	state.saw_forward_motion = prev_saw_forward_motion;
	state.last_bet_or_raise_increment = prev_last_bet_or_raise_increment; // Restore this crucial field

	// 3. Revert player-specific contributions and stack
	// Calculate how much this player contributed in the forward step
	let amount_contributed_by_player =
		state.total_contribution[player_who_acted] - prev_total_contribution_player;
	state.stacks[player_who_acted] += amount_contributed_by_player;
	state.total_contribution[player_who_acted] = prev_total_contribution_player;
	state.ante[player_who_acted] = prev_ante_player; // Restore player's specific per-round contribution

	// 4. Re-evaluate all_in status for the player who acted
	state.all_in[player_who_acted] = state.stacks[player_who_acted] == 0;
	// Also, if they were marked all_in due to stack < min_future_wager, this needs to be undone.
	// The simple stacks[p] == 0 check might cover it if stack is restored correctly.
	// If they were marked all_in because they contributed their full stack, this is fine.
	// If they were marked all_in because stack < min_wager, and stack is now >= min_wager, they are not all_in.
	// This requires re-evaluating the min_future_wager condition if we want to be precise.
	// For now, `stacks[p] == 0` is the primary all-in condition upon undo.

	// 5. Handle fold reversal
	if was_folded {
		state.folded[player_who_acted] = false;
		state.remaining_players += 1;
		// Re-check all_in status if a fold was undone, as their stack is now relevant again.
		state.all_in[player_who_acted] = state.stacks[player_who_acted] == 0;
	}

	// 6. Betting sequence and action history
	// The round for betting sequence is state.round *after* potential transition undo.
	let round_for_seq = if let Some(ref pre_round) = round_transition_state {
		pre_round.round
	} else {
		state.round
	};
	if round_for_seq < state.config_num_rounds && state.betting_len[round_for_seq] > 0 {
		state.betting_len[round_for_seq] -= 1;
		let len = state.betting_len[round_for_seq] as usize;
		if len < MAX_ACTIONS_PER_ROUND {
			// Should always be true if len was > 0
			state.betting_sequence[round_for_seq][len] = BETTING_SEQ_SENTINEL;
		}
	} else {
		log::error!(
			"[UNDO_BET] Error decrementing betting sequence for round {}. Len: {:?}",
			round_for_seq,
			state.betting_len.get(round_for_seq)
		);
	}
	state.action_history.pop();

	// 7. Restore current_player to whose turn it was *before* this action
	state.current_player = prev_player_turn;

	// 8. If a transition was undone, ensure terminal state is also undone
	if resolve_transition_state.is_some() && state.current_player != TERMINAL_PLAYER_ID {
		// If we undid a resolve, but current_player is not terminal (e.g. restored to player's turn),
		// then winner and eval cache should reflect the pre-resolve state.
		// This is already handled by restoring pre_resolve fields.
		// If winner was Some, it's restored. If it was None, it's restored.
	}
	if round_transition_state.is_some() && state.current_player == TERMINAL_PLAYER_ID {
		// This case implies undoing a deal that led to a terminal state, then undoing the bet that led to the deal.
		// If current_player is now CHANCE, winner should be None.
		if state.current_player == CHANCE_PLAYER_ID {
			state.winner = None;
			// If config_vector_cards is false, evaluated_hands was restored from PreResolveState (which would be None if this path is hit).
			// If config_vector_cards is true, evaluated_hands was NOT restored from PreResolveState by the logic above.
			// It holds the values from the showdown. If we are now in a CHANCE node (meaning a deal is next),
			// these evaluations are for a completed board and are stale. They must be cleared.
			if state.config_vector_cards {
				state.evaluated_hands = [None; MAX_SEATS]; // Clear if vector_cards and now CHANCE
			                                   //  log::trace!("[UNDO_BET] CHANCE node after round transition undo with vector_cards=true. Cleared evaluated_hands.");
			} else {
				// If not vector_cards, it was restored from PreResolveState. If that PreResolveState
				// was from a bet that *didn't* lead to showdown but to a new round, its evaluated_hands
				// would be None. If it *did* lead to showdown, then this path (round_transition_state.is_some())
				// shouldn't be hit. For safety, if we are transitioning to CHANCE, clear it.
				state.evaluated_hands = [None; MAX_SEATS];
				//  log::trace!("[UNDO_BET] CHANCE node after round transition undo with vector_cards=false. Cleared evaluated_hands for safety.");
			}
		}
	}

	// Perf: This log involves many arguments and formatting, can be costly. Commented out.
	// log::debug!("[UNDO_BET] P{} action {:?} undone. CurrentPlayer P{}, Stakes={}, Pot={}, NumRaises={}, LastBetInc={}",
	//     player_who_acted, move_type, state.current_player, state.stakes, state.pot, state.num_raises, state.last_bet_or_raise_increment);
}

```

crates/games/src/hulh/state/core.rs:
```
#![allow(unreachable_code)]

//! Core HulhState struct definition and main trait implementations.

use crate::hulh::{
	action::{self, HulhMove, GRID_HULH},           // Import action module, HulhMove and GRID_HULH
	constants::*,
	game::HulhGame,
	settings::RaiseRuleType,                      // <-- Import RaiseRuleType
	state::{betting, dealing, infoset, showdown}, // Import submodules
	undo::UndoRecord,                             // Import undo types
	CALL_ACTION,                                  // Import CALL_ACTION for BB option check
};
use crate::hulh::{constants::MAX_SEATS, settings::DeckType}; // Add BROKEN_MAX_SEATS import and DeckType
use crate::Chips; // Use Chips from crate root
use engine::{
	abstraction::InformationAbstraction, // Import trait
	error::{GameError, GameResult},
	game::Game, // <-- Import Game trait
	policy::PackedPolicy,
	state::State,
	// Use ConcreteActionsAndProbs, remove ActionsAndProbs
	types::{
		ConcreteAction, ConcreteActionsAndProbs, InfosetHashKey, PlayerId, Prob, Utility,
		CHANCE_PLAYER_ID, TERMINAL_PLAYER_ID,
	}, // Keep engine types
};
use fastcards::{
	card::Card,
	fast_deck::{DynPartialEq, FastDeck, FastDeckTrait}, // Import FastDeckTrait, DynPartialEq
	hole_cards::HoleCards, // Added import for HoleCards
	HandRank,
};
use log;
use std::fmt;
// use rand::Rng; // Removed unused import
use cfr_rng::CfrRngPool; // <-- MODIFIED THIS IMPORT
use smallvec::SmallVec;
// abs_diff_eq removed

// Pot Struct ---

#[derive(Debug, Clone, PartialEq, Eq)] // Add Eq
pub struct Pot {
	pub amount: Chips, // Make pub for test access
	// List of seat indices eligible to win this pot
	pub contenders: SmallVec<[PlayerId; MAX_SEATS]>, // Make pub for test access
	                                                 // Winners are no longer stored on the Pot struct; they are determined on-the-fly in calculate_returns.
	                                                 // pub winners: SmallVec<[PlayerId; BROKEN_MAX_SEATS]>,
}

// Betting Context Struct ---

/// Betting context information for a player
#[derive(Debug, Clone, Copy)]
pub struct BettingContext {
	pub facing_bet: bool,
	pub is_bb_option: bool,
	pub current_stake: Chips,
	pub pot_size: Chips,
}

// --- HulhState Struct ---

pub struct HulhState {
	pub num_players: usize,
	pub dealer_btn: PlayerId,

	// --- Config (copied from HulhGame settings) ---
	pub config_num_rounds: usize,
	pub config_board_cards_per_round: Vec<usize>,
	pub config_small_blind: Chips,
	pub config_big_blind: Chips,
	// pub config_raise_sizes: Vec<Chips>, // Replaced by config_fixed_raise_amounts
	pub config_fixed_raise_amounts: Vec<Chips>,
	pub config_opening_bet_sizes: Vec<Vec<Chips>>,
	pub config_raise_rule: RaiseRuleType,
	pub config_max_raises: Vec<usize>,
	pub config_starting_stack: Chips,
	pub config_num_hole_cards: usize,
	pub config_deck_type: DeckType,
	/// Copied from `HulhSettings`. If true, indicates that `vector_hole_cards`
	/// and `vector_board_cards` were populated at the start and should be used
	/// for dealing, ensuring a fixed sequence through undo/redo.
	pub config_vector_cards: bool,

	// --- Core State ---
	pub current_player: PlayerId,
	pub round: usize, // 0=Pre-flop, 1=Flop, 2=Turn, 3=River
	pub vector_hole_cards: [[Option<Card>; MAX_HOLE_CARDS]; MAX_SEATS],
	pub vector_board_cards: [Option<Card>; MAX_BOARD_CARDS],
	pub current_vector_hole_card_deal_idx: usize, // Tracks hole cards dealt from vector
	pub current_vector_board_card_deal_idx: usize, // Tracks board cards dealt from vector
	pub deck: Box<dyn FastDeckTrait>, // Use trait object for the deck (now only board cards after init)
	pub private_cards: [[Option<Card>; MAX_HOLE_CARDS]; MAX_SEATS], // Revealed private cards
	pub board_cards: [Card; MAX_BOARD_CARDS],
	pub board_cards_len: u8,
	pub cards_dealt_this_round: usize,

	// --- Betting State ---
	pub num_raises: usize, // Raises in current round
	pub stakes: Chips,     // Current bet level required to call (total for the round)
	pub pot: Chips,
	pub ante: [Chips; MAX_SEATS],
	pub total_contribution: [Chips; MAX_SEATS],
	pub folded: [bool; MAX_SEATS],
	pub remaining_players: usize,
	pub betting_sequence: Vec<[ConcreteAction; MAX_ACTIONS_PER_ROUND]>,
	pub betting_len: Vec<u8>,
	pub last_raiser: Option<PlayerId>,
	pub bb_checked_preflop: bool,
	pub last_bet_or_raise_increment: Chips,

	// --- Phase 4 State ---
	// pending_oot field removed
	pub saw_forward_motion: bool,

	// --- Chip Management ---
	pub(crate) stacks: [Chips; MAX_SEATS], // Chips still available
	pub all_in: [bool; MAX_SEATS], // True once stack == 0 - Made pub
	// pub pots: SmallVec<[Pot; BROKEN_MAX_SEATS + 1]>, // Removed: Pots are built on demand in calculate_returns

	// --- Terminal State ---
	pub winner: Option<PlayerId>,
	pub evaluated_hands: [Option<HandRank>; MAX_SEATS],

	// --- Undo support ---
	pub undo_stack: SmallVec<[UndoRecord; 16]>,

	// --- Unified Action History (Phase 8) ---
	/// Stores the sequence of (PlayerId, ConcreteAction) tuples representing
	/// both chance events (deals) and player decisions. Required by the
	/// `State::history()` method. Capacity chosen to accommodate maximum
	/// possible actions in a HULH hand (deals + betting rounds).
	pub action_history: SmallVec<[(PlayerId, ConcreteAction); 128]>,
	/// Stores pre-formatted strings for display in `to_string()`, ensuring
	/// "Bet" vs "Raise" is accurate based on context at the time of action.
	pub display_action_history: SmallVec<[String; 128]>,
}

impl HulhState {
	/// Show‑order required by Phase‑6 rules.
	// pub fn showdown_order(&self) -> Vec<PlayerId> {
	//     showdown::calculate_show_order(self)
	// }
	#[inline]
	pub fn sb_player(&self) -> PlayerId {
		// Made pub
		crate::hulh::constants::small_blind(self.dealer_btn, self.num_players)
	}
	#[inline]
	pub fn bb_player(&self) -> PlayerId {
		crate::hulh::constants::big_blind(self.dealer_btn, self.num_players)
	}
	#[inline]
	pub fn first_to_act_preflop(&self) -> PlayerId {
		crate::hulh::constants::first_to_act_preflop(self.dealer_btn, self.num_players)
	}
	#[inline]
	pub fn first_to_act_postflop(&self) -> PlayerId {
		crate::hulh::constants::first_to_act_postflop(self.dealer_btn, self.num_players)
	}

	/// Creates a new initial state for HULH.
	/// Accepts the game instance to access settings like num_players.
	pub(crate) fn new(game: &HulhGame, dealer_btn: PlayerId, rng_pool: &mut CfrRngPool) -> Self {
		let settings = game.settings(); // Access via public method
		let num_players = settings.num_players; // Get num_players from game settings
		assert!((2..=MAX_SEATS).contains(&num_players), "num_players {} not in range 2..={}", num_players, MAX_SEATS);
		assert!(dealer_btn < num_players, "dealer_btn {} >= num_players {}", dealer_btn, num_players);

		// --- Deck Initialization ---
		// The main_deck is used for sampling if `config_vector_cards` is false,
		// or for cards beyond those pre-assigned by `vector_cards`.
		// To externally fix the order of cards dealt from this deck (e.g., for
		// specific testing scenarios), a rigged `FastDeck` implementation should be
		// provided here.

		// Create the deck instance based on type, then shuffle it.
		let mut deck_instance = match settings.deck_type {
			DeckType::Standard52 => FastDeck::new_ordered(),
			DeckType::ShortDeck36 => FastDeck::new_short_ordered(),
		};
		deck_instance.shuffle_with_cfr_rng(rng_pool); // Shuffle the deck using passed-in rng_pool

		// Box the shuffled deck.
		let mut main_deck: Box<dyn FastDeckTrait> = Box::new(deck_instance);
		// At this point, main_deck is shuffled.

		// --- Pre-assign Hole Cards if vector_cards is true ---
		// When `vector_cards` is true, all hole and board cards for the hand
		// are determined here, at the beginning of the game. These cards are stored
		// in `vector_hole_cards` and `vector_board_cards` and will be dealt in this
		// fixed order, irrespective of undo/apply action cycles. This ensures
		// the card sequence is not re-sampled.
		let mut sample_card_vector = [[None; MAX_HOLE_CARDS]; MAX_SEATS];
		let mut vector_board_cards = [None; MAX_BOARD_CARDS];
		if settings.vector_cards {
			let sb_player_val = crate::hulh::constants::small_blind(dealer_btn, num_players);
			for card_idx in 0..settings.num_hole_cards {
				for player_offset in 0..num_players {
					let player_receiving = (sb_player_val + player_offset) % num_players;
					if !main_deck.is_empty() {
						let card = main_deck.deal_card();
						sample_card_vector[player_receiving][card_idx] = Some(card);
					} else {
						panic!("Deck ran out of cards during pre-assignment of hole cards.");
					}
				}
			}

			let mut current_board_card_idx = 0;
			// Iterate over the number of cards to deal for each street (flop, turn, river)
			for num_cards_this_street in settings.board_cards_per_round.iter() {
				for _ in 0..*num_cards_this_street {
					// Ensure we do not exceed the capacity of vector_board_cards
					if current_board_card_idx < MAX_BOARD_CARDS {
						if !main_deck.is_empty() {
							let card = main_deck.deal_card();
							vector_board_cards[current_board_card_idx] = Some(card);
							current_board_card_idx += 1;
						} else {
							// This panic is appropriate: not enough cards in the main deck for pre-assignment.
							panic!("Deck ran out of cards during pre-assignment of board cards.");
						}
					} else {
						// This panic means the sum of board_cards_per_round exceeds MAX_BOARD_CARDS.
						// This should ideally be caught earlier, e.g., in HulhSettings validation or HulhGame::new.
						let total_requested_board_cards: usize =
							settings.board_cards_per_round.iter().sum();
						panic!(
                            "Attempting to pre-assign more board cards ({}) than MAX_BOARD_CARDS ({}) allows. Check HulhSettings.board_cards_per_round.",
                            total_requested_board_cards, MAX_BOARD_CARDS
                        );
					}
				}
			}
			// Log the pre-assigned cards
			let _p0_log_card = if settings.num_hole_cards > 0 {
				sample_card_vector[0][0]
			} else {
				None
			};
			let _p1_log_card = if num_players > 1 && settings.num_hole_cards > 0 {
				sample_card_vector[1][0]
			} else {
				None
			};
			// log::trace!(
			// 	"[HulhState::new] Pre-assigned hole cards (first card): P0={:?}, P1={:?}",
			// 	p0_log_card,
			// 	p1_log_card
			// );
			// log::trace!(
			// 	"[HulhState::new] Pre-assigned board cards {:?} {:?} {:?} {:?} {:?}",
			// 	vector_board_cards[0],
			// 	vector_board_cards[1],
			// 	vector_board_cards[2],
			// 	vector_board_cards[3],
			// 	vector_board_cards[4]
			// );
		} else {
			// log::trace!(
			// 	"Not pre-assigning hole cards because use_pre_assigned_hole_cards is false."
			// );
		}
		// The main `state.deck` (which will be `main_deck`) remains full and is not modified by pre-assignment.

		let mut total_contribution = [0; MAX_SEATS];
		let mut pot = 0;
		let mut stacks = [0; MAX_SEATS];
		let mut folded = [false; MAX_SEATS];
		let mut all_in = [false; MAX_SEATS]; // To be calculated after antes/blinds

		// Initialize stacks for active players
		for slot in stacks.iter_mut().take(num_players) {
			*slot = settings.starting_stack; // Use settings.starting_stack
		}
		for seat in num_players..MAX_SEATS {
			folded[seat] = true;
			all_in[seat] = true;
		}
		let remaining_players = num_players;

		// --- Ante and Blind Posting ---
		// 1. Collect Game Antes (if any)
		if settings.ante > 0 {
			for p in 0..num_players {
				let ante_to_post = settings.ante.min(stacks[p]);
				stacks[p] = stacks[p].saturating_sub(ante_to_post); // Use saturating_sub
				total_contribution[p] += ante_to_post;
				pot += ante_to_post;
			}
		}

		// 2. Post Blinds (if any)
		// `round_ante_commitment` stores the amounts posted as blinds for the current round commitment.
		let mut round_ante_commitment = [0; MAX_SEATS];
		let sb = crate::hulh::constants::small_blind(dealer_btn, num_players);
		let bb = crate::hulh::constants::big_blind(dealer_btn, num_players);
		
		log::trace!("[HulhState::new] Dealer button: {}, SB: {}, BB: {}", dealer_btn, sb, bb);

		if settings.small_blind > 0 {
			let sb_amount = settings.small_blind.min(stacks[sb]);
			round_ante_commitment[sb] = sb_amount;
			total_contribution[sb] += sb_amount; // Add to total contribution
			pot += sb_amount;
			stacks[sb] = stacks[sb].saturating_sub(sb_amount); // Use saturating_sub
			log::trace!("[HulhState::new] SB P{} posted ${}, stack now: {}", sb, sb_amount, stacks[sb]);
		}

		if settings.big_blind > 0 {
			let bb_amount = settings.big_blind.min(stacks[bb]);
			round_ante_commitment[bb] = bb_amount;
			total_contribution[bb] += bb_amount; // Add to total contribution
			pot += bb_amount;
			stacks[bb] = stacks[bb].saturating_sub(bb_amount); // Use saturating_sub
			log::trace!("[HulhState::new] BB P{} posted ${}, stack now: {}", bb, bb_amount, stacks[bb]);
		}

		// Determine initial all-in status based on final stacks after antes and blinds
		for p in 0..num_players {
			all_in[p] = stacks[p] == 0; // All-in if stack is exactly 0
		}

		// Pots are no longer initialized here; they are built on demand.
		
		log::trace!("[HulhState::new] Initial state - Stakes: {}, Pot: {}, Antes: {:?}", 
			settings.big_blind, pot, &round_ante_commitment[..num_players]);

		HulhState {
			num_players,
			dealer_btn,
			config_num_rounds: settings.num_rounds,
			config_board_cards_per_round: settings.board_cards_per_round.clone(),
			config_small_blind: settings.small_blind,
			config_big_blind: settings.big_blind,
			// config_raise_sizes: settings.raise_sizes.clone(), // Replaced
			config_fixed_raise_amounts: settings.fixed_raise_amounts.clone(), // Initialize new field
			config_opening_bet_sizes: settings.opening_bet_sizes.clone(),     // Initialize new field
			config_raise_rule: settings.raise_rule,                           // Initialize new field
			config_max_raises: settings.max_raises.clone(),
			config_starting_stack: settings.starting_stack,
			config_num_hole_cards: settings.num_hole_cards,
			config_deck_type: settings.deck_type, // Initialize from settings
			config_vector_cards: settings.vector_cards, // Copy setting
			current_player: CHANCE_PLAYER_ID,
			round: 0,
			vector_hole_cards: sample_card_vector, // Store pre-assigned cards (populated if vector_cards is true)
			vector_board_cards, // Store pre-assigned cards (populated if vector_cards is true)
			current_vector_hole_card_deal_idx: 0, // Initialize new field
			current_vector_board_card_deal_idx: 0, // Initialize new field
			deck: main_deck,    // Main deck, full if pre-assignment happened from a temp deck
			private_cards: [[None; MAX_HOLE_CARDS]; MAX_SEATS], // Revealed cards start as None
			num_raises: 0,
			// Stakes are the amount to call. If big_blind is 0 (e.g. ante only games), stakes are 0.
			stakes: settings.big_blind,
			pot,
			board_cards: [Card::from_bits(0); MAX_BOARD_CARDS], // Use MAX_BOARD_CARDS for fixed array dim
			board_cards_len: 0,
			cards_dealt_this_round: 0,
			ante: round_ante_commitment, // This is HulhState.ante (per-round commitment)
			total_contribution,
			folded,
			remaining_players,
			winner: None,
			evaluated_hands: [None; MAX_SEATS], // Initialize hand evaluation cache
			betting_sequence: vec![
				[BETTING_SEQ_SENTINEL; MAX_ACTIONS_PER_ROUND];
				settings.num_rounds
			], // Vec, BROKEN_ for inner dim
			betting_len: vec![0; settings.num_rounds], // Vec
			last_raiser: None,
			bb_checked_preflop: false,
			last_bet_or_raise_increment: if settings.big_blind > 0 {
				settings.big_blind
			} else {
				0
			}, // Initialize new field
			// pending_oot removed
			saw_forward_motion: false,
			stacks,
			all_in, // Initialize based on blinds
			// pots: initial_pots, // Removed
			undo_stack: SmallVec::new(),
			action_history: SmallVec::new(), // Initialize empty history
			display_action_history: SmallVec::new(), // Initialize empty display history
		}
	}

	/// Returns the number of raises that have occurred so far in the
	/// current betting round.  This method existed in the pre‑refactor
	/// monolithic implementation and is still required by downstream
	/// crates (e.g. poker‑abs) that have not yet migrated to the new
	/// public API.  Keeping it here maintains backward compatibility
	/// while we gradually phase the old interface out.
	#[inline]
	pub fn raises_so_far(&self) -> usize {
		self.num_raises
	}

	#[inline]
	pub(crate) fn seats(&self) -> core::ops::Range<usize> {
		0..self.num_players
	}

	/// Appends action to the current round's sequence.
	pub(crate) fn sequence_append_move(&mut self, action: ConcreteAction) {
		if self.round < self.config_num_rounds {
			let len = self.betting_len[self.round] as usize;
			if len < MAX_ACTIONS_PER_ROUND {
				self.betting_sequence[self.round][len] = action;
				self.betting_len[self.round] += 1;
			} else {
				panic!(
					"Betting sequence exceeded fixed capacity: {} {}",
					self.round, len
				);
			}
		}
	}

	/// Helper: compute legal actions as if `p` were the current player
	pub fn legal_actions_for(&self, p: PlayerId) -> Vec<ConcreteAction> {
		let mut tmp = self.clone();
		tmp.current_player = p;
		tmp.legal_actions()
	}

	#[inline]
	pub(crate) fn clear_round_local_flags(&mut self) {
		// pending_oot removed
		self.saw_forward_motion = false;
	}

	// --- Public Getters for Testing ---
	pub fn round(&self) -> usize {
		self.round
	}
	pub fn dealer_btn(&self) -> PlayerId {
		self.dealer_btn
	}

	pub fn board_cards(&self) -> &[Card] {
		&self.board_cards[..self.board_cards_len as usize]
	}
	pub fn board_cards_len(&self) -> u8 {
		self.board_cards_len
	}
	pub fn private_cards(&self) -> &[[Option<Card>; MAX_HOLE_CARDS]; MAX_SEATS] {
		&self.private_cards
	}
	pub fn pot(&self) -> Chips {
		self.pot
	}
	/// Return folded flags only for active seats
	pub fn folded(&self) -> &[bool] {
		&self.folded[..self.num_players]
	}
	pub fn betting_sequence(&self) -> &Vec<[ConcreteAction; MAX_ACTIONS_PER_ROUND]> {
		&self.betting_sequence
	}
	pub fn winner(&self) -> Option<PlayerId> {
		self.winner
	}
	pub fn num_raises(&self) -> usize {
		self.num_raises
	}
	pub fn stakes(&self) -> Chips {
		self.stakes
	}
	/// Return ante only for active seats
	pub fn ante(&self) -> &[Chips] {
		&self.ante[..self.num_players]
	}
	/// Return total commitment only for active seats
	pub fn total_contribution(&self) -> &[Chips] {
		&self.total_contribution[..self.num_players]
	}
	/// Betting lengths per round (tests)
	pub fn betting_len(&self) -> &[u8] {
		&self.betting_len
	}
	/// Expose remaining deck for test helpers
	pub fn deck_available_cards(&self) -> Vec<Card> {
		// Return Vec<Card>
		self.deck.available_cards_vec() // Use trait method
	}
	pub fn cards_dealt_this_round(&self) -> usize {
		self.cards_dealt_this_round
	}
	pub fn debug_saw_forward_motion(&self) -> bool {
		self.saw_forward_motion
	}
	// Does `player` still have chips to put in this betting round?
	#[inline]
	pub fn facing_bet(&self, player: PlayerId) -> bool {
		betting::facing_bet(self, player)
	}

	/// Returns `true` if the fixed-limit raise cap for the current betting
	/// round applies and has been reached.
	///
	/// Note: The cap is generally lifted in heads-up play or once a
	/// multi-way pot becomes heads-up.
	#[inline]
	pub fn is_raise_cap_reached(&self) -> bool {
		betting::raise_cap_reached(self)
	}

	/// Returns the chip stacks of all active players as a slice.
	pub fn stacks(&self) -> &[Chips] {
		&self.stacks[..self.num_players]
	}

	/// Returns the stack size of a specific player.
	/// Returns `None` if the `player_id` is out of bounds.
	pub fn get_stack(&self, player_id: PlayerId) -> Option<Chips> {
		if player_id < self.num_players {
			Some(self.stacks[player_id])
		} else {
			None
		}
	}

	pub fn all_in(&self) -> &[bool] {
		&self.all_in[..self.num_players]
	}

	/// Debug helper: mutable access to stacks (used by integration tests)
	#[doc(hidden)]
	pub fn stacks_mut(&mut self) -> &mut [Chips; MAX_SEATS] {
		&mut self.stacks
	}

	// Add a getter for pots for testing
	// #[doc(hidden)]
	// pub fn pots(&self) -> &SmallVec<[Pot; MAX_SEATS + 1]> {
	//     &self.pots // Removed as pots field is gone
	// }

	/// Returns the current length of the undo stack (for testing/debugging).
	pub fn undo_stack_len(&self) -> usize {
		self.undo_stack.len()
	}

	#[doc(hidden)]
	pub fn force_split_pot(&mut self, pot_amount: Chips) {
		// This function now sets up the state such that calculate_returns()
		// will naturally result in a split pot.
		// Assumes a 2-player game for simplicity of this test helper.
		assert_eq!(
			self.num_players, 2,
			"force_split_pot test helper currently assumes 2 players"
		);

		self.winner = Some(0); // Arbitrary winner for terminal state, actual returns determined by hands/pots
						 // Give both players the same, unbeatable hand rank (e.g., Royal Flush or lowest rank value)
		let best_rank: HandRank = 0; // Assuming 0 is the best possible rank
		self.evaluated_hands[0] = Some(best_rank);
		self.evaluated_hands[1] = Some(best_rank);
		// Other players (if any, though asserted 2p) would have None or worse.

		// Set total contributions for the two players
		self.total_contribution[0] = pot_amount / 2;
		self.total_contribution[1] = pot_amount / 2;
		for i in 2..self.num_players {
			// Zero out others
			self.total_contribution[i] = 0;
		}

		// Ensure players 0 and 1 are not folded and are the only remaining players
		self.folded[0] = false;
		self.folded[1] = false;
		for i in 2..MAX_SEATS {
			// Fold any other potential players
			self.folded[i] = true;
		}
		self.remaining_players = 2;

		// Mark players 0 and 1 as all-in if their contribution matches their starting stack
		// For simplicity, assume they started with enough and are now all-in for pot_amount / 2.0
		// This part might need adjustment based on how STARTING_STACK is used in tests.
		// If STARTING_STACK is pot_amount / 2, then they are all-in.
		// Or, more simply for a test helper, just mark them as all-in if they contributed.
		self.all_in[0] = self.total_contribution[0] > 0;
		self.all_in[1] = self.total_contribution[1] > 0;

		self.current_player = engine::types::TERMINAL_PLAYER_ID;
	}

	#[doc(hidden)]
	/// Force‑set the current player (testing of OOT scenarios only)
	pub fn set_current_player_for_test(&mut self, p: PlayerId) {
		self.current_player = p;
	}

	/// Apply a betting move **as a specific player** even if that player is
	/// not the current in‑turn actor.  Intended only for validation / test
	/// harnesses (Phase‑7 OOT scenarios).
	///
	/// WARNING: Do **not** expose this in production UIs – it bypasses turn
	/// checks on purpose.
	pub fn apply_action_as(&mut self, player: PlayerId, mv: HulhMove) -> GameResult<()> {
		// Reverted to simpler implementation as OOT test is removed.
		log::debug!(
			"apply_action_as: current_player={}, act_as={}, mv={:?}",
			self.current_player,
			player,
			mv
		);
		crate::hulh::state::betting::apply_bet(self, player, mv)
	}

	// --- Test-only Helper Methods ---
	// #[cfg(test)] // Removed cfg(test) to make it available for integration tests
	pub fn get_current_pot_structure_for_test(&self) -> SmallVec<[Pot; MAX_SEATS + 1]> {
		// This method allows tests to see the pot structure based on current contributions and folded status.
		// log::trace!(
		//     "[get_current_pot_structure_for_test] Calling build_side_pots with: num_players={}, total_contribution={:?}, folded={:?}",
		//     self.num_players,
		//     &self.total_contribution[..], // Log the whole array
		//     &self.folded[..]              // Log the whole array
		// );
		showdown::build_side_pots(self.num_players, &self.total_contribution, &self.folded)
	}

	// #[cfg(test)] // Removed cfg(test)
	pub fn set_evaluated_hands_for_test(&mut self, new_hands: [Option<HandRank>; MAX_SEATS]) {
		self.evaluated_hands = new_hands;
	}

	// #[cfg(test)] // Removed cfg(test)
	pub fn set_winner_for_test(&mut self, winner: Option<PlayerId>) {
		self.winner = winner;
	}

	// #[cfg(test)] // Removed cfg(test)
	pub fn set_remaining_players_for_test(&mut self, remaining: usize) {
		self.remaining_players = remaining;
	}

	// #[cfg(test)] // Removed cfg(test)
	pub fn set_current_player_terminal_for_test(&mut self) {
		self.current_player = TERMINAL_PLAYER_ID;
	}

	/// Calculates a bucket index for the opponent's hole cards.
	///
	/// - For 1 hole card, returns the card's rank index.
	/// - For 2 hole cards (e.g., Hold'em), returns the `HoleCards::get_index()`.
	/// - Returns `u16::MAX` if cards are not available or player ID is invalid.
	pub fn opponent_hole_bucket(&self, opponent_player_id: PlayerId) -> u16 {
		if opponent_player_id >= self.num_players {
			return u16::MAX; // Invalid player
		}

		match self.config_num_hole_cards {
			1 => {
				// Single hole card
				if let Some(card) = self.private_cards[opponent_player_id][0] {
					card.rank_index() as u16
				} else {
					u16::MAX // Card not dealt
				}
			}
			2 => {
				// Hold'em-like
				if let (Some(c0), Some(c1)) = (
					self.private_cards[opponent_player_id][0],
					self.private_cards[opponent_player_id][1],
				) {
					HoleCards::new(c0, c1).get_index() as u16
				} else {
					u16::MAX // Cards not fully dealt
				}
			}
			_ => u16::MAX, // Unsupported number of hole cards for this bucketing
		}
	}
	
	// --- Betting Context Methods ---
	
	/// Returns whether the player is facing a bet (needs to call)
	pub fn is_facing_bet(&self, player: PlayerId) -> bool {
		betting::facing_bet(self, player)
	}
	
	/// Returns true if this is BB checking their option preflop
	pub fn is_bb_option(&self, player: PlayerId, action: ConcreteAction) -> bool {
		self.round == 0 && 
		player == self.bb_player() && 
		!self.is_facing_bet(player) && 
		action == CALL_ACTION
	}
	
	/// Returns structured betting context for the given player and action
	pub fn get_betting_context(&self, player: PlayerId, action: ConcreteAction) -> BettingContext {
		let facing_bet = self.is_facing_bet(player);
		let is_bb_option = self.is_bb_option(player, action);
		
		BettingContext {
			facing_bet,
			is_bb_option,
			current_stake: self.stakes,
			pot_size: self.pot,
		}
	}
	
	// --- Showdown Methods ---
	
	/// Returns true if the hand reached showdown (2+ players on river)
	pub fn reached_showdown(&self) -> bool {
		self.is_terminal() && self.remaining_players > 1 && self.round >= 3
	}
	
	/// Returns which players went to showdown
	pub fn went_to_showdown(&self) -> Vec<bool> {
		if self.reached_showdown() {
			(0..self.num_players).map(|i| !self.folded[i]).collect()
		} else {
			vec![false; self.num_players]
		}
	}
}

impl State for HulhState {
	type Game = HulhGame;

	fn num_players(&self) -> usize {
		self.num_players
	}

	fn current_player(&self) -> PlayerId {
		self.current_player
	}

	fn apply_action(&mut self, action_val: ConcreteAction) -> GameResult<()> {
		let player_id_for_log = self.current_player();
		// Added trace log for apply_action entry
		// log::trace!("[HulhState::apply_action ENTRY] Player: {:?}, Action: {:?} ({}), Round: {}, Stakes: {}, Ante[P0]: {}, Ante[P1]: {}",
		//     player_id_for_log,
		//     action_val,
		//     self.action_to_string(player_id_for_log, action_val),
		//     self.round,
		//     self.stakes,
		//     self.ante.first().copied().unwrap_or(0), // Safe access for logging
		//     self.ante.get(1).copied().unwrap_or(0)  // Safe access for logging
		// );

		if self.is_terminal() {
			return Err(GameError::InvalidState(
				"Cannot apply action to terminal state".to_string(),
			));
		}

		// Runtime check: Ensure the action being applied is actually legal
		// Skip this check for chance nodes with vector_cards enabled, as legal_actions() would panic
		if !(self.is_chance_node() && self.config_vector_cards) {
			let legal_actions = self.legal_actions();
			if !legal_actions.contains(&action_val) {
				return Err(GameError::InvalidAction { action: action_val });
			}
		}

		// #[cfg(debug_assertions)]
		// {
		// 	let action_str_for_display = self.action_to_string(player_id_for_log, action_val);
		// 	let street_name = match self.round {
		// 		0 => "Preflop",
		// 		1 => "Flop",
		// 		2 => "Turn",
		// 		3 => "River",
		// 		_ => "Unknown",
		// 	};
		// 	log::debug!(
		// 		"[HAND_HISTORY] P{} {} on {}",
		// 		player_id_for_log,
		// 		action_str_for_display,
		// 		street_name
		// 	);
		// }

		let result = if player_id_for_log == CHANCE_PLAYER_ID {
			dealing::deal_card(self, action_val)
		} else {
			let mv = match action_val {
				a if a == action::FOLD_ACTION => HulhMove::Fold,
				a if a == action::CALL_ACTION => HulhMove::Call,
				a if a == action::RAISE_ACTION => HulhMove::Raise,
				_ => return Err(GameError::InvalidAction { action: action_val }),
			};
			let bet_result = betting::apply_bet(self, player_id_for_log, mv);

			#[cfg(debug_assertions)]
			if bet_result.is_ok() {
				let _action_str_for_display = self.action_to_string(player_id_for_log, action_val);
				// Re-evaluate for trace if needed
				// log::trace!(
				// 	"[POST_ACTION] P{} did {}. Stack: {}, AllIn: {}",
				// 	player_id_for_log,
				// 	action_str_for_display,
				// 	self.stacks[player_id_for_log],
				// 	self.all_in[player_id_for_log]
				// );
			}
			bet_result
		};

		if result.is_ok() {
			#[cfg(debug_assertions)]
			{
				let _action_str_for_display = self.action_to_string(player_id_for_log, action_val);
				let player_prefix = if player_id_for_log == CHANCE_PLAYER_ID {
					"C".to_string()
				} else {
					format!("P{}", player_id_for_log)
				};
				self.display_action_history
					.push(format!("{}:{}", player_prefix, _action_str_for_display));
			}
		}
		// log::trace!(
		// 	"[HulhState::apply_action EXIT] Player: {:?}, Action: {:?}, Result: {:?}",
		// 	player_id_for_log,
		// 	action_val,
		// 	result.is_ok()
		// );
		result
	}

	fn legal_actions(&self) -> Vec<ConcreteAction> {
		match self.current_player {
			TERMINAL_PLAYER_ID => Vec::new(),
			CHANCE_PLAYER_ID => {
				// Modified for vector.md
				dealing::get_chance_outcomes(self) // This now returns Vec<ConcreteAction>
					.into_iter()
					.map(|(action, _prob)| action) // We only need actions here
					.collect()
			}
			player => {
				// Direct enumeration of legal actions for HULH
				if self.folded[player] {
					return Vec::new();
				}

				let mut actions = Vec::with_capacity(3); // Fold, Call, Raise

				if self.all_in[player] {
					if betting::facing_bet(self, player) {
						actions.push(action::FOLD_ACTION);
					} else {
						actions.push(action::CALL_ACTION); // Check when all-in
					}
				} else {
					let facing_bet_val = betting::facing_bet(self, player);
					
					log::trace!("[legal_actions] P{} - Round: {}, Stakes: {}, Ante[P{}]: {}, Facing bet: {}", 
						player, self.round, self.stakes, player, self.ante[player], facing_bet_val);

					if facing_bet_val {
						log::trace!("[legal_actions] P{} is facing a bet", player);
						actions.push(action::FOLD_ACTION);
						log::trace!("[legal_actions] P{} - Added FOLD", player);
						
						if betting::player_can_call(self, player) {
							actions.push(action::CALL_ACTION);  // Call the bet
							log::trace!("[legal_actions] P{} - Added CALL", player);
						} else {
							log::trace!("[legal_actions] P{} - Cannot CALL (all-in)", player);
						}
						
						let cap_reached = betting::raise_cap_reached(self);
						let can_raise = betting::player_can_raise(self, player);
						log::trace!("[legal_actions] P{} - Raise check: cap_reached={}, can_raise={}", 
							player, cap_reached, can_raise);
							
						if !cap_reached && can_raise {
							actions.push(action::RAISE_ACTION);
							log::trace!("[legal_actions] P{} - Added RAISE", player);
						}
					} else {
						// Not facing a bet
						log::trace!("[legal_actions] P{} is NOT facing a bet", player);
						
						if betting::player_can_call(self, player) {
							actions.push(action::CALL_ACTION);  // Check (call 0)
							log::trace!("[legal_actions] P{} - Added CALL (check)", player);
						} else {
							log::trace!("[legal_actions] P{} - Cannot CALL/CHECK (all-in)", player);
						}
						
						// In fixed-limit games, we use RAISE even when not facing a bet
						// This represents the opening bet
						let cap_reached = betting::raise_cap_reached(self);
						let can_raise = betting::player_can_raise(self, player);
						log::trace!("[legal_actions] P{} - Bet check: cap_reached={}, can_raise={}", 
							player, cap_reached, can_raise);
							
						if !cap_reached && can_raise {
							actions.push(action::RAISE_ACTION);
							log::trace!("[legal_actions] P{} - Added RAISE (opening bet)", player);
						}
					}
				}
				
				log::trace!("[legal_actions] P{} - Final actions before sort: {:?}", player, actions);
				
				actions.sort_unstable();
				actions.dedup();
				actions
			}
		}
	}

	fn action_to_string(&self, player: PlayerId, action_val: ConcreteAction) -> String {
		if player == CHANCE_PLAYER_ID {
			if let Some(card) = Card::from_standard_deck_index(action_val.0 as usize) {
				format!("Deal:{}", card)
			} else {
				format!("Deal:Invalid({})", action_val.0)
			}
		} else {
			match action_val {
				a if a == action::FOLD_ACTION => "Fold".to_string(),
				a if a == action::CALL_ACTION => {
					if betting::facing_bet(self, player) {
						"Call".to_string()
					} else {
						"Check".to_string()  // Display as Check for UI clarity
					}
				}
				a if a == action::RAISE_ACTION => {
					// Determine if this is an opening bet or a raise
					// If the player is not facing a bet, then this is an opening bet
					let is_opening_bet = !betting::facing_bet(self, player);
					
					// Calculate the amount
					let raise_increment = match self.config_raise_rule {
						RaiseRuleType::FixedAmount => {
							if self.round < self.config_fixed_raise_amounts.len() {
								self.config_fixed_raise_amounts[self.round]
							} else {
								0
							} // Should not happen if action is legal
						}
						RaiseRuleType::DoublePreviousBetOrRaise => {
							if self.last_bet_or_raise_increment > 0 {
								self.last_bet_or_raise_increment * 2
							} else {
								0
							} // Should not happen if action is legal (Raise needs prior increment)
						}
						RaiseRuleType::MatchPreviousBetOrRaise => {
							if self.last_bet_or_raise_increment > 0 {
								self.last_bet_or_raise_increment
							} else {
								0
							} // Should not happen if action is legal
						}
					};
					let raise_to_amount = self.stakes + raise_increment;
					
					if is_opening_bet {
						format!("Bet {}", raise_to_amount)
					} else {
						format!("Raise To {}", raise_to_amount)
					}
				}
				_ => format!("Invalid({})", action_val.0),
			}
		}
	}

	fn is_terminal(&self) -> bool {
		self.winner.is_some()
	}

	fn returns(&self) -> Vec<Utility> {
		showdown::calculate_returns(self)
	}

	fn rewards(&self) -> Vec<Utility> {
		vec![0.0; self.num_players]
	}

	fn is_chance_node(&self) -> bool {
		self.current_player == CHANCE_PLAYER_ID
	}

	/// Recursively explores chance nodes from the current state until decision nodes are reached.
	/// For each decision node, it computes the `InfosetHashKey` for the current player using
	/// the provided `InformationAbstraction` and returns a list of `(InfosetHashKey, State)` pairs.
	///
	/// This is useful for identifying all unique initial decision points after chance events.
	///
	/// # Arguments
	/// * `info_abs`: The information abstraction to use for generating infoset keys.
	///
	/// # Returns
	/// A `Vec` containing tuples of `(InfosetHashKey, Vec<ConcreteAction>)`.
	/// The `InfosetHashKey` is for the player at the decision node.
	/// The `Vec<ConcreteAction>` is the sequence of all chance actions taken on the path
	/// to reach that decision node.
	/// The list is deduplicated by `InfosetHashKey`; only the first encountered path
	/// for each key is retained.
	fn get_initial_decision_nodes_abstracted<I: InformationAbstraction<Self::Game> + ?Sized>(
		&self,
		info_abs: &I,
		player_for_infoset: PlayerId, // This is the "hero"
	) -> Vec<(InfosetHashKey, Vec<ConcreteAction>)>
	where
		Self: Sized,
	{
		// Use a HashMap for deduplication based on InfosetHashKey.
		// Stores the key and the path of chance actions that led to it.
		let mut collected_nodes_map = std::collections::HashMap::new();

		// Recursive helper function to build the list of abstracted decision nodes.
		fn recurse_abstract_nodes<IA: InformationAbstraction<HulhGame> + ?Sized>(
			current_state: &HulhState, // current_state is &HulhState as this is in impl State for HulhState
			info_abs: &IA,
			hero_player_id: PlayerId, // Pass the hero player ID
			collected_nodes_map: &mut std::collections::HashMap<
				InfosetHashKey,
				Vec<ConcreteAction>,
			>,
		) {
			if current_state.is_terminal() {
				return; // Stop if terminal
			}

			if !current_state.is_chance_node() {
				// This is a decision node.
				let acting_player = current_state.current_player();

				// Only generate key and path if it's the specified hero's turn.
				if acting_player == hero_player_id {
					let key = info_abs.key(current_state, hero_player_id);

					// Deduplicate: only insert if the key is new.
					collected_nodes_map.entry(key).or_insert_with(|| {
						let mut hero_specific_chance_actions = Vec::new();
						let mut num_hole_cards_processed_in_history = 0;

						for (history_entry_actor_id, history_entry_action) in
							current_state.history().iter()
						{
							if *history_entry_actor_id == CHANCE_PLAYER_ID {
								// Check if this chance action is a hole card deal
								if num_hole_cards_processed_in_history
									< current_state.num_players()
										* current_state.config_num_hole_cards
								{
									// It's a hole card deal. Determine recipient.
									let recipient_player_offset =
										num_hole_cards_processed_in_history
											% current_state.num_players();
									let recipient_player = (current_state.sb_player()
										+ recipient_player_offset)
										% current_state.num_players();

									if recipient_player == hero_player_id {
										hero_specific_chance_actions.push(*history_entry_action);
									}
									num_hole_cards_processed_in_history += 1;
								} else {
									// It's a board card deal. These are public and not "for" the hero.
									// Do not add to hero_specific_chance_actions.
								}
							}
						}
						hero_specific_chance_actions
					});
				}
				// If not hero's turn, simply return.
				return;
			}

			// This is a chance node; explore its outcomes.
			for (action, _prob) in current_state.chance_outcomes() {
				let mut next_state = current_state.clone();
				match next_state.apply_action(action) {
					Ok(()) => {
						recurse_abstract_nodes(
							&next_state,
							info_abs,
							hero_player_id,
							collected_nodes_map,
						);
					}
					Err(_e) => {
						// Log or handle error if action application fails.
						// For a default implementation, skipping the path is reasonable.
						// Example: log::warn!("Failed to apply chance action {:?} during node collection: {}", action, _e);
					}
				}
			}
		}

		recurse_abstract_nodes(self, info_abs, player_for_infoset, &mut collected_nodes_map);

		// Convert the HashMap to the desired Vec format.
		collected_nodes_map.into_iter().collect()
	}

	fn bucketed_chance_outcomes<I: InformationAbstraction<HulhGame> + ?Sized>(
		&self,
		info_abs: &I,
	) -> ConcreteActionsAndProbs {
		/// A compact *bucketed* version of `get_chance_outcomes`.
		///
		///    – All cards that lead to the **same information-state key *and* the same
		///      opponent-private-bucket** are merged into one outcome.
		///    – The probability of the aggregated outcome is the **sum** of the raw
		///      probabilities (they still add up to 1.0).
		///    – The concrete action we return is simply the *first* card that fell
		///      into that bucket.  Any unique representative is fine: after the
		///      abstraction the IS-MDP cares only about the bucket, not the exact card.
		///
		/// IMPORTANT:
		///     • You must call the *same* bucket functions here that you used during
		///       CFR training, otherwise exploitability is computed on a different
		///       game!
		///     • This helper panics when `config_vector_cards == true`, exactly like
		///       the original.
		use std::collections::HashMap;

		if self.current_player != CHANCE_PLAYER_ID {
			return Vec::new();
		}
		if self.config_vector_cards {
			panic!(
				"get_chance_outcomes called while `config_vector_cards` is true; \
                use `sample_chance_action` instead."
			);
		}

		// --------------------------------------------------------------------
		// 1. Group every still-available card by our abstraction key
		// --------------------------------------------------------------------
		// Key =  (best-responder’s infoset key,  opponent private bucket id)
		//
		// •  The infoset-key must be the *bucketed / abstract* key returned by the
		//    Information-Abstraction you trained on.
		// •  The opponent’s private bucket id makes sure we never merge two worlds
		//    that are distinguishable to the opponent.
		//
		// For HU-LHE this is usually something like
		//       (street, public-bucket, opp_hole_bucket)
		// encoded in a 64-bit `InfosetHashKey`.
		//
		// You already have helper functions that compute those numbers – plug them
		// in where the TODOs are.
		#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
		struct BucketKey {
			info_key_for_br: InfosetHashKey,
			opp_hole_bucket: u16,
		}

		let mut grouped: HashMap<BucketKey, (ConcreteAction, Prob)> = HashMap::new();

		let num_avail = self.deck.len();
		if num_avail == 0 {
			log::warn!(
				"get_chance_outcomes called with empty deck (round {}, cards_dealt_this_round {}).",
				self.round,
				self.cards_dealt_this_round
			);
			return Vec::new();
		}
		let single_prob = 1.0 / num_avail as Prob;

		let mut tmp = self.clone();
		for (a, _) in self.chance_outcomes() {
			tmp.apply_action(a)
				.expect("Failed to apply action in bucketed_chance_outcomes");

			let player_id = tmp.current_player;
			let opponent = (player_id + 1) % self.num_players;

			let br_info_key = info_abs.key(&tmp, player_id);
			let opp_hole_bucket = tmp.opponent_hole_bucket(opponent);

			let key = BucketKey {
				info_key_for_br: br_info_key,
				opp_hole_bucket,
			};

			// 3.  store the *first* card per bucket and accumulate probability
			grouped
				.entry(key)
				.and_modify(|e| e.1 += single_prob)
				.or_insert((a, single_prob)); // Use 'a' which is the ConcreteAction

			tmp.undo_last_action()
				.expect("Failed to undo action in bucketed_chance_outcomes");
		}

		// --------------------------------------------------------------------
		// 2. Convert aggregated map back into ConcreteActionsAndProbs
		// --------------------------------------------------------------------
		let mut result: ConcreteActionsAndProbs =
			grouped.into_iter().map(|(_, (act, p))| (act, p)).collect();

		// Optional: keep deterministic order for reproducibility
		result.sort_by_key(|&(ConcreteAction(idx), _)| idx);

		// Assert that the sum of probabilities is 1.0
		let prob_sum: Prob = result.iter().map(|&(_, p)| p).sum();
		debug_assert!(
			(prob_sum - 1.0).abs() < 1e-9, // Use a small epsilon for float comparison
			"Aggregated probabilities in bucketed_chance_outcomes do not sum to 1.0. Sum: {}, Outcomes: {:?}",
			prob_sum,
			result
		);

		// log::trace!(
		// "[bucketed_get_chance_outcomes] Shrunk {} original chance outcomes into {} bucketed outcomes.",
		// num_avail, // Original number of available cards from deck
		// result.len() // Number of outcomes after bucketing
		// );

		result
	}

	fn chance_outcomes(&self) -> ConcreteActionsAndProbs {
		dealing::get_chance_outcomes(self)
	}

	fn information_state_key(&self, player: PlayerId) -> InfosetHashKey {
		infoset::calculate_infoset_key(self, player)
	}

	fn history(&self) -> &[(PlayerId, ConcreteAction)] {
		&self.action_history
	}

	fn sample_chance_action(
		&self,
		rng_pool: &cfr_rng::CfrRngPool,
	) -> Option<(ConcreteAction, Prob)> {
		dealing::sample_chance_action(self, rng_pool)
	}

	fn to_string(&self) -> String {
		let mut s = String::new();
		s.push_str("--- HULH State ---\n");
		for p in 0..self.num_players {
			let cards_str: Vec<String> = self.private_cards[p]
				.iter()
				.map(|&opt| opt.map_or("?".to_string(), |c| format!("{}", c)))
				.collect();
			s.push_str(&format!("P{} Cards: [{}]\n", p, cards_str.join(" ")));
		}
		let board_str: Vec<String> = (0..self.board_cards_len as usize)
			.map(|i| format!("{}", self.board_cards[i]))
			.collect();
		s.push_str(&format!("Board: [{}]\n", board_str.join(" ")));
		s.push_str("Action History: ");
		if self.display_action_history.is_empty() {
			s.push_str("<none>");
		} else {
			s.push_str(&self.display_action_history.join(", "));
		}
		s.push('\n');
		s.push_str(&format!("Round: {}\n", self.round));
		s.push_str(&format!("Player: {:?}\n", self.current_player));
		s.push_str(&format!("Pot: {}\n", self.pot));
		s.push_str(&format!("Stakes (Round): {}\n", self.stakes));
		s.push_str("Antes (Round): ");
		s.push_str(
			&self.ante[..self.num_players]
				.iter()
				.map(|a| format!("{}", a))
				.collect::<Vec<_>>()
				.join(" "),
		);
		s.push('\n');
		s.push_str("Total Contrib: ");
		s.push_str(
			&self.total_contribution[..self.num_players]
				.iter()
				.map(|a| format!("{}", a))
				.collect::<Vec<_>>()
				.join(" "),
		);
		s.push('\n');
		s.push_str("Folded: ");
		s.push_str(
			&self.folded[..self.num_players]
				.iter()
				.map(|f| f.to_string())
				.collect::<Vec<_>>()
				.join(" "),
		);
		s.push('\n');
		s.push_str(&format!("Num Raises (Round): {}\n", self.num_raises));
		s.push_str(&format!("Last Raiser (Round): {:?}\n", self.last_raiser));
		s.push_str("Stacks: ");
		s.push_str(
			&self.stacks[..self.num_players]
				.iter()
				.map(|st| format!("{}", st))
				.collect::<Vec<_>>()
				.join(" "),
		);
		s.push('\n');
		s.push_str("All In: ");
		s.push_str(
			&self.all_in[..self.num_players]
				.iter()
				.map(|ai| ai.to_string())
				.collect::<Vec<_>>()
				.join(" "),
		);
		s.push('\n');
		if self.is_terminal() {
			s.push_str("Terminal: true\n");
			s.push_str(&format!("Winner: {:?}\n", self.winner));
			s.push_str(&format!("Returns: {:?}\n", self.returns()));
		} else {
			s.push_str("Terminal: false\n");
		}
		s.push_str("------------------\n");
		s
	}

	fn undo_last_action(&mut self) -> GameResult<()> {
		match self.undo_stack.pop() {
			Some(record) => {
				match record {
					UndoRecord::DealPrivate {
						player,
						card_pos,
						card,
						prev_player,
					} => {
						dealing::undo_deal_private(self, player, card_pos, card, prev_player);
					}
					UndoRecord::DealPublic { card, prev_player } => {
						dealing::undo_deal_public(self, card, prev_player);
					}
					UndoRecord::Bet {
						move_type,
						player,
						prev_stakes,
						prev_pot,
						prev_ante,
						prev_total_contribution,
						prev_num_raises,
						prev_last_raiser,
						prev_bb_checked_preflop,
						prev_saw_forward_motion,
						was_folded,
						prev_player,
						round_transition_state,
						resolve_transition_state,
						prev_last_bet_or_raise_increment, // Added for undo
					} => {
						betting::undo_bet(
							self,
							move_type,
							player,
							prev_stakes,
							prev_pot,
							prev_ante,
							prev_total_contribution,
							prev_num_raises,
							prev_last_raiser,
							prev_bb_checked_preflop,
							prev_saw_forward_motion,
							was_folded,
							prev_player,
							round_transition_state,
							resolve_transition_state,
							prev_last_bet_or_raise_increment, // Pass to undo_bet
						);
					}
				}
				#[cfg(debug_assertions)]
				{
					if !self.display_action_history.is_empty() {
						self.display_action_history.pop();
					} else {
						// This log might still be useful even in release if an undo happens on an empty display history,
						// indicating a potential logic error if display_action_history is expected to mirror undo_stack.
						// However, if display_action_history is purely for debug, this warning is also debug-only.
						log::warn!("UndoRecord processed, but display_action_history is empty.");
					}
				}
				Ok(())
			}
			None => Err(GameError::LogicError(
				"Cannot undo from initial state".into(),
			)),
		}
	}

	fn debug_string_with_actions(&self, packed_policy: &PackedPolicy) -> String {
		let mut s = String::new();
		s.push_str("--------------------------------------------------\n");
		s.push_str("HULH State Details:\n");
		s.push_str(&self.to_string());
		let current_player = self.current_player();
		s.push_str(&format!("Current Player: {:?}\n", current_player));
		s.push_str("\nActions & Probabilities (from PackedPolicy):\n");
		if packed_policy.num_actions == 0 {
			s.push_str("  <No actions provided or terminal state>\n");
		} else {
			for (idx, &prob) in packed_policy.probabilities.iter().enumerate() {
				// Map index to concrete action from GRID_HULH
				let concrete_action = if idx < GRID_HULH.len() {
					GRID_HULH[idx]
				} else {
					continue; // Skip invalid indices
				};
				let action_str = self.action_to_string(current_player, concrete_action);
				s.push_str(&format!(
					"  - Action: {} ({}), Prob: {:.4}\n",
					action_str, concrete_action.0, prob
				));
			}
			let prob_sum: f64 = packed_policy.probabilities.iter().sum();
			if !packed_policy.probabilities.is_empty() && (prob_sum - 1.0).abs() > 1e-4 {
				s.push_str(&format!(
					"  Warning: Probabilities sum to {:.4}\n",
					prob_sum
				));
			}
		}
		s.push_str("--------------------------------------------------");
		s
	}
}

// Manual implementation of Debug for concise output
impl fmt::Debug for HulhState {
	fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
		f.debug_struct("HulhState")
			.field("player", &self.current_player)
			.field("dealer_btn", &self.dealer_btn)
			.field("round", &self.round)
			.field("pre_assigned_P0", &self.vector_hole_cards[0]) // For debug
			.field("pre_assigned_P1", &self.vector_hole_cards[1]) // For debug
			.field("vec_hole_idx", &self.current_vector_hole_card_deal_idx) // For debug
			.field("vec_board_idx", &self.current_vector_board_card_deal_idx) // For debug
			.field("private(P0)", &self.private_cards[0])
			.field("private(P1)", &self.private_cards[1])
			.field(
				"board",
				&(&self.board_cards[..self.board_cards_len as usize]),
			)
			.field("deck_len", &self.deck.len()) // More concise deck debug
			.field("history_len", &self.action_history.len())
			.field("pot", &self.pot)
			.field("stakes", &self.stakes)
			.field("stacks", &&self.stacks[..self.num_players])
			.field("all_in", &&self.all_in[..self.num_players])
			.field("winner", &self.winner)
			.field("ranks_P0", &self.evaluated_hands[0]) // For debug
			.field("ranks_P1", &self.evaluated_hands[1]) // For debug
			.finish()
	}
}

impl PartialEq for HulhState {
	fn eq(&self, other: &Self) -> bool {
		if std::ptr::eq(self, other) {
			return true;
		}
		self.current_player == other.current_player &&
        self.dealer_btn == other.dealer_btn &&
        self.round == other.round &&
        self.vector_hole_cards == other.vector_hole_cards && // Compare pre-assigned
        self.current_vector_hole_card_deal_idx == other.current_vector_hole_card_deal_idx &&
        self.current_vector_board_card_deal_idx == other.current_vector_board_card_deal_idx &&
        self.num_raises == other.num_raises &&
        self.stakes == other.stakes &&
        self.pot == other.pot &&
        self.board_cards_len == other.board_cards_len &&
        self.board_cards[..self.board_cards_len as usize] == other.board_cards[..other.board_cards_len as usize] &&
        DynPartialEq::eq(self.deck.as_ref(), other.deck.as_ref()) && // Deck now only board cards
        self.private_cards == other.private_cards && // Revealed cards
        self.cards_dealt_this_round == other.cards_dealt_this_round &&
        self.ante == other.ante &&
        self.total_contribution == other.total_contribution &&
        self.folded == other.folded &&
        self.remaining_players == other.remaining_players &&
        self.winner == other.winner &&
        self.evaluated_hands == other.evaluated_hands && // Compare eval cache
        (0..self.config_num_rounds).all(|r| {
            let len_self = self.betting_len[r] as usize;
            let len_other = other.betting_len[r] as usize;
            len_self == len_other && self.betting_sequence[r][..len_self] == other.betting_sequence[r][..len_other]
        }) &&
        self.betting_len == other.betting_len &&
        self.last_raiser == other.last_raiser &&
        self.bb_checked_preflop == other.bb_checked_preflop &&
        self.last_bet_or_raise_increment == other.last_bet_or_raise_increment &&
        self.saw_forward_motion == other.saw_forward_motion &&
        self.stacks == other.stacks &&
        self.all_in == other.all_in &&
        self.config_num_rounds == other.config_num_rounds &&
        self.config_board_cards_per_round == other.config_board_cards_per_round &&
        self.config_small_blind == other.config_small_blind &&
        self.config_big_blind == other.config_big_blind &&
        self.config_fixed_raise_amounts == other.config_fixed_raise_amounts &&
        self.config_opening_bet_sizes == other.config_opening_bet_sizes &&
        self.config_raise_rule == other.config_raise_rule &&
        self.config_max_raises == other.config_max_raises &&
        self.config_starting_stack == other.config_starting_stack &&
        self.config_num_hole_cards == other.config_num_hole_cards &&
        self.config_deck_type == other.config_deck_type &&
        self.config_vector_cards == other.config_vector_cards && // Compare new field
        self.action_history == other.action_history
	}
}

impl Eq for HulhState {}

impl Clone for HulhState {
	fn clone(&self) -> Self {
		Self {
			num_players: self.num_players,
			dealer_btn: self.dealer_btn,
			config_num_rounds: self.config_num_rounds,
			config_board_cards_per_round: self.config_board_cards_per_round.clone(),
			config_small_blind: self.config_small_blind,
			config_big_blind: self.config_big_blind,
			config_fixed_raise_amounts: self.config_fixed_raise_amounts.clone(),
			config_opening_bet_sizes: self.config_opening_bet_sizes.clone(),
			config_raise_rule: self.config_raise_rule,
			config_max_raises: self.config_max_raises.clone(),
			config_starting_stack: self.config_starting_stack,
			config_num_hole_cards: self.config_num_hole_cards,
			config_deck_type: self.config_deck_type,
			config_vector_cards: self.config_vector_cards, // Clone new field
			current_player: self.current_player,
			round: self.round,
			vector_hole_cards: self.vector_hole_cards, // Clone pre-assigned cards
			vector_board_cards: self.vector_board_cards, // Clone pre-assigned board cards
			current_vector_hole_card_deal_idx: self.current_vector_hole_card_deal_idx, // Clone new field
			current_vector_board_card_deal_idx: self.current_vector_board_card_deal_idx, // Clone new field
			deck: self.deck.clone_box(),               // Clone deck (board cards)
			private_cards: self.private_cards,         // Clone revealed cards
			num_raises: self.num_raises,
			stakes: self.stakes,
			pot: self.pot,
			board_cards: self.board_cards,
			board_cards_len: self.board_cards_len,
			cards_dealt_this_round: self.cards_dealt_this_round,
			ante: self.ante,
			total_contribution: self.total_contribution,
			folded: self.folded,
			remaining_players: self.remaining_players,
			winner: self.winner,
			evaluated_hands: self.evaluated_hands, // Clone eval cache
			betting_sequence: self.betting_sequence.clone(),
			betting_len: self.betting_len.clone(),
			last_raiser: self.last_raiser,
			bb_checked_preflop: self.bb_checked_preflop,
			last_bet_or_raise_increment: self.last_bet_or_raise_increment,
			saw_forward_motion: self.saw_forward_motion,
			stacks: self.stacks,
			all_in: self.all_in,
			undo_stack: self.undo_stack.clone(),
			action_history: self.action_history.clone(),
			display_action_history: self.display_action_history.clone(),
		}
	}
}

```

crates/games/src/hulh/state/dealing.rs:
```
//! Logic for handling chance nodes (dealing cards) in HULH.

use super::core::HulhState;
use crate::hulh::{
	constants::MAX_BOARD_CARDS, // Import specific constants // Removed BROKEN_NUM_HOLE_CARDS
	undo::UndoRecord,
};
use engine::{
	error::{GameError, GameResult},
	types::{ConcreteAction, ConcreteActionsAndProbs, Prob, CHANCE_PLAYER_ID}, // Removed InfosetHashKey
	                                                                          // Removed: abstraction::InformationAbstraction,
};
// Removed: use crate::HulhGame;
use fastcards::card::Card;
// use rand::Rng; // Removed unused import
use log;
// Removed unused: use engine::state::State; // Import the State trait

/// Applies a chance action (dealing a specific card).
pub(crate) fn deal_card(state: &mut HulhState, action: ConcreteAction) -> GameResult<()> {
	let prev_player_for_undo = state.current_player; // Store before potential change
	state.cards_dealt_this_round += 1;

	// Use state.config_num_hole_cards to determine total hole cards to deal
	let total_hole_cards_to_deal = state.num_players * state.config_num_hole_cards;
	// Count how many hole cards have already been dealt (revealed)
	let cards_revealed_so_far = state
		.private_cards
		.iter()
		.take(state.num_players) // Only consider active players
		.flat_map(|player_cards| player_cards.iter().take(state.config_num_hole_cards))
		.filter(|c| c.is_some())
		.count();
		

	if cards_revealed_so_far < total_hole_cards_to_deal {
		// --- Deal (Reveal) Private Card ---
		let card_pos = cards_revealed_so_far / state.num_players;
		let player_receiving_offset = cards_revealed_so_far % state.num_players;
		let player_receiving = (state.sb_player() + player_receiving_offset) % state.num_players;
		

		// Card to deal is directly from the action
		let card_dealt = match Card::from_standard_deck_index(action.0 as usize) {
			Some(c) => c,
			None => return Err(GameError::InvalidAction { action }), // Invalid card ID in action
		};

		if state.config_vector_cards {
			// log::trace!("[deal_card_H_VEC] Dealing hole card from vector: {:?}. Prev CVHCDI: {}", card_dealt, state.current_vector_hole_card_deal_idx);
		}

		// Remove the card from the main state.deck. This must happen for consistency.
		if !state.config_vector_cards {
			// log::trace!("[deal_card HOLE] Attempting to remove card_dealt={:?} (action.0={}) from deck. Deck (len={}) before: {:?}", card_dealt, action.0, state.deck.len(), state.deck.available_cards_vec());
			if !state.deck.remove_card_from_deck(card_dealt) {
				log::error!("Failed to remove card {:?} (from action for hole card) from deck. Deck state: {:?}", card_dealt, state.deck.available_cards_vec());
				return Err(GameError::LogicError(
					"Card from action (hole card) not found in deck for removal.".into(),
				));
			}
			// log::trace!("[deal_card HOLE] Successfully removed {:?}. Deck (len={}) after: {:?}", card_dealt, state.deck.len(), state.deck.available_cards_vec());
		}

		state.private_cards[player_receiving][card_pos] = Some(card_dealt);
		state.undo_stack.push(UndoRecord::DealPrivate {
			player: player_receiving,
			card_pos,
			card: card_dealt, // Card that was actually dealt and recorded
			prev_player: prev_player_for_undo,
		});
		state.action_history.push((CHANCE_PLAYER_ID, action));

		if state.config_vector_cards {
			state.current_vector_hole_card_deal_idx += 1;
			// log::trace!("[deal_card_H_VEC] Incremented CVHCDI to: {}. Total hole cards to deal: {}", state.current_vector_hole_card_deal_idx, total_hole_cards_to_deal);
		}

		let transition_condition = (cards_revealed_so_far + 1) == total_hole_cards_to_deal;
		if transition_condition {
			let first = state.first_to_act_preflop();
			state.current_player = if !state.folded[first] {
				first
			} else {
				super::round::next_betting_player(state, first)
			};
			let active_with_chips = state
				.seats()
				.filter(|&p| !state.folded[p] && !state.all_in[p])
				.count();
			if active_with_chips <= 1 {
				crate::hulh::state::round::start_next_round(state);
			}
		} else {
			state.current_player = CHANCE_PLAYER_ID;
		}
	} else {
		// --- Deal Public (Board) Card ---
		// Card to deal is directly from the action
		let card_dealt = match Card::from_standard_deck_index(action.0 as usize) {
			Some(c) => c,
			None => return Err(GameError::InvalidAction { action }), // Invalid card ID in action
		};

		if state.config_vector_cards {
			// log::trace!("[deal_card_B_VEC] Dealing board card from vector: {:?}. Prev CVBCDI: {}", card_dealt, state.current_vector_board_card_deal_idx);
		}

		// Remove the card from the main state.deck. This must happen for consistency.
		if !state.config_vector_cards {
			// log::trace!("[deal_card BOARD] Attempting to remove card_dealt={:?} (action.0={}) from deck. Deck (len={}) before: {:?}", card_dealt, action.0, state.deck.len(), state.deck.available_cards_vec());
			if !state.deck.remove_card_from_deck(card_dealt) {
				log::error!(
                    "BOARD‑CARD‑REMOVAL‑FAIL: id={} card={:?} round={} dealt_this_round={} deck_len={} top10={:?}",
                    action.0, card_dealt, state.round, state.cards_dealt_this_round,
                    state.deck.len(),
                    &state.deck.available_cards()[0..state.deck.available_cards().len().min(10)]
                );
				// Using a more specific error message to distinguish from hole card removal failure
				return Err(GameError::LogicError(
					"Card from action (board card) not found in deck for removal.".into(),
				));
			}
			// log::trace!("[deal_card BOARD] Successfully removed {:?}. Deck (len={}) after: {:?}", card_dealt, state.deck.len(), state.deck.available_cards_vec());
		}

		state.undo_stack.push(UndoRecord::DealPublic {
			card: card_dealt,
			prev_player: prev_player_for_undo,
		});
		state.action_history.push((CHANCE_PLAYER_ID, action));
		state.board_cards[state.board_cards_len as usize] = card_dealt;
		state.board_cards_len += 1;
		// Note: board_len_for_eval_cache is not touched here. resolve_showdown handles it.

		if state.config_vector_cards {
			state.current_vector_board_card_deal_idx += 1;
			// log::trace!("[deal_card_B_VEC] Incremented CVBCDI to: {}. Vector board cards len: {}", state.current_vector_board_card_deal_idx, state.vector_board_cards.len());
		}

		let expected_cards_this_round = state
			.config_board_cards_per_round
			.get(state.round)
			.copied()
			.unwrap_or(0);
		if expected_cards_this_round == 0 {
			let first = state.first_to_act_postflop();
			state.current_player = if !state.folded[first] {
				first
			} else {
				super::round::next_betting_player(state, first)
			};
			let active_players_with_chips = state
				.seats()
				.filter(|&p| !state.folded[p] && !state.all_in[p])
				.count();
			let betting_closed = active_players_with_chips <= 1;
			if betting_closed {
				if state.round == state.config_num_rounds - 1 {
					crate::hulh::state::showdown::resolve_showdown(state);
				} else {
					crate::hulh::state::round::start_next_round(state);
				}
			}
		} else if state.cards_dealt_this_round == expected_cards_this_round {
			let first = state.first_to_act_postflop();
			state.current_player = if !state.folded[first] {
				first
			} else {
				super::round::next_betting_player(state, first)
			};
			let active_players_with_chips = state
				.seats()
				.filter(|&p| !state.folded[p] && !state.all_in[p])
				.count();
			let betting_closed = active_players_with_chips <= 1;
			if betting_closed {
				if state.round == state.config_num_rounds - 1 {
					crate::hulh::state::showdown::resolve_showdown(state);
				} else {
					crate::hulh::state::round::start_next_round(state);
				}
			}
		} else {
			state.current_player = CHANCE_PLAYER_ID;
		}
	}

	Ok(())
}

/// Undoes the dealing (revealing) of a private card.
pub(crate) fn undo_deal_private(
	state: &mut HulhState,
	player: engine::types::PlayerId,
	card_pos: usize,
	card_that_was_revealed: Card,          // Use this to add back to deck
	_prev_player: engine::types::PlayerId, // prev_player is used to set state.current_player
) {
	state.private_cards[player][card_pos] = None; // Un-reveal
	state.evaluated_hands[player] = None; // Invalidate this player's cached hand strength

	// IMPORTANT: Only add the card back to state.deck if config_vector_cards is false.
	// If config_vector_cards is true, the card was sourced from vector_hole_cards
	// and was *never removed* from state.deck (which holds only leftover cards).
	if !state.config_vector_cards {
		// log::trace!("[undo_deal_private] config_vector_cards=false. Adding {:?} back to deck.", card_that_was_revealed);
		if !state.deck.add_card_to_deck(card_that_was_revealed) {
			// This would be a critical error, means the deck state is inconsistent
			log::error!("Failed to add private card {:?} back to deck during undo (config_vector_cards=false). Deck state: {:?}", card_that_was_revealed, state.deck.available_cards_vec());
			// Consider panicking or returning an error if undo can fail
		}
	} else {
		// log::trace!("[undo_deal_private] config_vector_cards=true. Card {:?} was from vector, not adding back to state.deck.", card_that_was_revealed);
	}

	state.cards_dealt_this_round -= 1;
	state.action_history.pop();

	if state.config_vector_cards {
		// log::trace!("[undo_deal_private_VEC] Undoing deal of {:?}. Prev CVHCDI: {}", card_that_was_revealed, state.current_vector_hole_card_deal_idx);
		if state.current_vector_hole_card_deal_idx > 0 {
			state.current_vector_hole_card_deal_idx -= 1;
			// log::trace!("[undo_deal_private_VEC] Decremented CVHCDI to: {}", state.current_vector_hole_card_deal_idx);
		} else {
			log::warn!("[undo_deal_private_VEC] Attempted to decrement current_vector_hole_card_deal_idx below zero.");
		}
	}

	let total_hole_cards_to_deal = state.num_players * state.config_num_hole_cards;
	let cards_revealed_so_far = state
		.private_cards
		.iter()
		.take(state.num_players)
		.flat_map(|pc| pc.iter().take(state.config_num_hole_cards))
		.filter(|c| c.is_some())
		.count();

	let remaining_hole_cards_to_reveal = total_hole_cards_to_deal - cards_revealed_so_far;

	if remaining_hole_cards_to_reveal > 0 {
		state.current_player = CHANCE_PLAYER_ID;
	} else {
		let first = state.first_to_act_preflop();
		state.current_player = if !state.folded[first] {
			first
		} else {
			super::round::next_betting_player(state, first)
		};
	}
}

/// Undoes the dealing of a public (board) card.
pub(crate) fn undo_deal_public(
	state: &mut HulhState,
	card: Card,
	prev_player: engine::types::PlayerId,
) {
	// IMPORTANT: Only add the card back to state.deck if config_vector_cards is false.
	// If config_vector_cards is true, the card was sourced from vector_board_cards
	// and was *never removed* from state.deck (which holds only leftover cards).
	if !state.config_vector_cards {
		// log::trace!("[undo_deal_public] config_vector_cards=false. Adding {:?} back to deck.", card);
		let added_back = state.deck.add_card_to_deck(card); // Add back to board card deck
		debug_assert!(
			added_back,
			"Failed to add public card back to deck during undo (config_vector_cards=false)"
		);
		if !added_back {
			// Add runtime log for release builds if assert fails
			log::error!("CRITICAL: Failed to add public card {:?} back to deck during undo (config_vector_cards=false). Deck state: {:?}", card, state.deck.available_cards_vec());
		}
	} else {
		// log::trace!("[undo_deal_public] config_vector_cards=true. Card {:?} was from vector, not adding back to state.deck.", card);
	}

	state.board_cards_len -= 1;
	if (state.board_cards_len as usize) < MAX_BOARD_CARDS {
		state.board_cards[state.board_cards_len as usize] = Card::from_bits(0);
	}
	state.cards_dealt_this_round -= 1;
	state.action_history.pop();
	state.current_player = prev_player;

	if state.config_vector_cards {
		// log::trace!("[undo_deal_public_VEC] Undoing deal of {:?}. Prev CVBCDI: {}", card, state.current_vector_board_card_deal_idx);
		if state.current_vector_board_card_deal_idx > 0 {
			state.current_vector_board_card_deal_idx -= 1;
			// log::trace!("[undo_deal_public_VEC] Decremented CVBCDI to: {}", state.current_vector_board_card_deal_idx);
		} else {
			log::warn!("[undo_deal_public_VEC] Attempted to decrement current_vector_board_card_deal_idx below zero.");
		}
	}
	// When a public card is undone, all players' hand evaluations are now stale.
	for p in 0..state.num_players {
		state.evaluated_hands[p] = None;
	}
}

/// Returns the possible chance outcomes.
/// If called this overrides the vector card sampling.
pub(crate) fn get_chance_outcomes(state: &HulhState) -> ConcreteActionsAndProbs {
	if state.current_player != CHANCE_PLAYER_ID {
		return Vec::new();
	}

	// IMPORTANT: THIS FUNCTION MUST PANIC IF config_vector_cards IS TRUE.
	// This behavior is intentional and critical for the correct functioning
	// of systems that rely on `sample_chance_action` for deterministic vector card dealing.
	// Calling `get_chance_outcomes` in this mode implies a misunderstanding of the
	// dealing mechanism or an attempt to circumvent the pre-assigned card sequence.
	if state.config_vector_cards {
		panic!("get_chance_outcomes called with config_vector_cards is true. This should not happen. Use sample_chance_action for deterministic vector card dealing.");
	}

	// For both hole card and board card phases, outcomes are based on the current state.deck.
	// The enforcement of pre-assigned cards happens in `deal_card` if `use_pre_assigned_hole_cards` is true.
	let num_available = state.deck.len();
	if num_available == 0 {
		// This check is important for both phases.
		// If it's hole card phase and deck is empty, it's an error (should have been caught in new).
		// If it's board card phase and deck is empty, it's also an issue if cards are expected.
		log::warn!("get_chance_outcomes called with empty deck. Current round: {}, cards dealt this round: {}", state.round, state.cards_dealt_this_round);
		return Vec::new();
	}
	let prob = 1.0 / num_available as Prob;
	state
		.deck
		.available_cards_vec()
		.iter()
		.map(|card| (ConcreteAction(card.standard_deck_index() as u64), prob))
		.collect::<ConcreteActionsAndProbs>()
}

/// Samples a single chance action.
pub(crate) fn sample_chance_action(
	state: &HulhState,
	_rng_pool: &cfr_rng::CfrRngPool, // Prefixed rng_pool as it's not used
) -> Option<(ConcreteAction, Prob)> {
	if state.current_player != CHANCE_PLAYER_ID {
		return None;
	}

	let num_available = state.deck.len();
	// log::trace!("[sample_chance_action] num_available: {}", num_available);
	

	if state.config_vector_cards {
		// log::trace!("[sample_chance_action] config_vector_cards is true, sampling from vector cards.");
		// If `config_vector_cards` is true, cards are sourced from the
		// pre-determined `vector_hole_cards` or `vector_board_cards`.
		// This sequence is fixed at the start of the game and is not
		// re-sampled, even through undo/apply action cycles.
		let total_hole_cards_to_be_dealt_in_game = state.num_players * state.config_num_hole_cards;

		if state.current_vector_hole_card_deal_idx < total_hole_cards_to_be_dealt_in_game {
			// log::trace!("[sample_chance_action] Hole card phase from vector.");
			// Hole Card Phase from vector
			if state.config_num_hole_cards > 0 {
				// Ensure there are hole cards to deal
				// Determine which player and card position is next based on current_vector_hole_card_deal_idx
				// Dealing order: P0 gets card 0, P1 gets card 0, ..., Pn gets card 0,
				// then P0 gets card 1, P1 gets card 1, ...
				let card_pos_idx = state.current_vector_hole_card_deal_idx / state.num_players;
				let player_offset = state.current_vector_hole_card_deal_idx % state.num_players;
				let player_idx = (state.sb_player() + player_offset) % state.num_players;

				log::trace!(
				"[sample_chance_action_H_VEC_PRE_ACCESS] CVHCDI: {}, TotalHCD: {}, PlayerReceiving: {}, CardPosIdx: {}, SB: {}",
				state.current_vector_hole_card_deal_idx,
				total_hole_cards_to_be_dealt_in_game,
				player_idx,
				card_pos_idx,
				state.sb_player()
				);

				if player_idx < state.num_players && card_pos_idx < state.config_num_hole_cards {
					// Removed redundant inner if condition
					if let Some(card) = state.vector_hole_cards[player_idx][card_pos_idx] {
						// Card found in vector_hole_cards
						// log::trace!("[sample_chance_action] Vector hole card P{}[{}]: {:?}", player_idx, card_pos_idx, card);
						// IMPORTANT: The probability 1.0 / num_available (i.e., state.deck.len()) is INTENTIONAL.
						// It reflects the probability of this specific pre-assigned card being the next one
						// dealt IF the dealing process were to sample from the remaining `state.deck`.
						// Even though the card itself is deterministic from the vector, this probability
						// is used by some algorithms (e.g., CFR) to weight the path.
						// DO NOT CHANGE THIS TO 1.0.
						return Some((
							ConcreteAction(card.standard_deck_index() as u64),
							1.0 / num_available as Prob,
						));
					} else {
						// Debug: print the entire vector_hole_cards state
						log::error!("[sample_chance_action] vector_hole_cards[{}][{}] is None!", player_idx, card_pos_idx);
						for p in 0..state.num_players {
							log::error!("  Player {}: card[0]={:?}, card[1]={:?}", 
								p, 
								state.vector_hole_cards[p][0], 
								if state.config_num_hole_cards > 1 { state.vector_hole_cards[p][1] } else { None }
							);
						}
						panic!(
                            "[sample_chance_action] config_vector_cards is true, but vector_hole_cards[{}][{}] is None. current_vector_hole_card_deal_idx: {}",
                            player_idx, card_pos_idx, state.current_vector_hole_card_deal_idx
                        );
					}
				} else {
					// This path means calculated player_idx or card_pos_idx is out of bounds for configured players/hole_cards.
					// Or, config_num_hole_cards might be 0, which should have been caught by the outer
					// `state.current_vector_hole_card_deal_idx < total_hole_cards_to_be_dealt_in_game` condition if total_hole_cards_to_be_dealt_in_game is 0.
					panic!(
                        "[sample_chance_action] config_vector_cards is true, in hole card phase, but config_num_hole_cards is 0. current_vector_hole_card_deal_idx: {}",
                        state.current_vector_hole_card_deal_idx
                    );
				}
			}
			// If we are past hole card dealing phase (according to current_vector_hole_card_deal_idx)
		} else {
			// log::trace!("[sample_chance_action] Board card phase from vector.");
			// Board Card Phase from vector
			// log::trace!(
			// "[sample_chance_action_B_VEC_PRE_ACCESS] CVBCDI: {}, VectorBoardCardsLen: {}",
			// state.current_vector_board_card_deal_idx,
			// state.vector_board_cards.len()
			// );
			if state.current_vector_board_card_deal_idx < state.vector_board_cards.len() {
				if let Some(card) =
					state.vector_board_cards[state.current_vector_board_card_deal_idx]
				{
					// Card found in vector_board_cards
					// log::trace!("[sample_chance_action] Vector board card [{}]: {:?}", state.current_vector_board_card_deal_idx, card);
					// IMPORTANT: The probability 1.0 / num_available (i.e., state.deck.len()) is INTENTIONAL.
					// See comment above for hole cards. DO NOT CHANGE THIS TO 1.0.
					return Some((
						ConcreteAction(card.standard_deck_index() as u64),
						1.0 / num_available as Prob,
					));
				} else {
					panic!(
                        "[sample_chance_action] config_vector_cards is true, but vector_board_cards[{}] is None.",
                        state.current_vector_board_card_deal_idx
                    );
				}
			} else {
				// This means current_vector_board_card_deal_idx is >= vector_board_cards.len(),
				// implying all pre-assigned board cards have been "sampled".
				// This should ideally lead to a terminal state or an error if more cards are expected.
				// The current logic will fall through to deck sampling if not caught by a panic here.
				// For strict vector_card adherence, this might be a panic if the game isn't over.
				log::warn!("[sample_chance_action] Vector board card index [{}] is out of bounds for vector_board_cards (len {}). Falling through to deck sampling if deck is not empty.",
                    state.current_vector_board_card_deal_idx, state.vector_board_cards.len()
                );
				// To strictly enforce vector cards and panic if exhausted when more are needed:
				// panic!(
				//     "[sample_chance_action] config_vector_cards is true, but board card index [{}] is out of bounds for vector_board_cards (len {}). All vector board cards exhausted.",
				//     state.current_vector_board_card_deal_idx, state.vector_board_cards.len()
				// );
			}
		}
	}

	// --- Standard Deck Sampling (config_vector_cards == false) ---
	// When config_vector_cards is false, cards are sampled from state.deck.
	// IMPORTANT: state.deck is shuffled once when HulhState is created (e.g., in new_initial_state).
	// Subsequent calls to sample_chance_action (when config_vector_cards is false)
	// will deterministically peek the next card from this pre-shuffled sequence.
	// The `_rng_pool` parameter is NOT used in this path.
	// To introduce randomness at each chance node decision when config_vector_cards is false,
	// one would need to modify this function to use `_rng_pool.gen_range` to select
	// an index from `state.deck.available_cards_vec()`. However, the current design
	// relies on the initial shuffle for the sequence of cards.
	//
	// For external control over the card sequence in tests (e.g., rigging specific deals)
	// when config_vector_cards is false, the state.deck should be initialized with a
	// custom `FastDeckTrait` implementation that returns a desired sequence.
	// log::trace!("[sample_chance_action] config_vector_cards is false, peeking next card from pre-shuffled deck.");
	if num_available == 0 {
		log::warn!(
			"sample_chance_action called with empty deck (and vector cards not used/exhausted)."
		);
		panic!(
			"sample_chance_action called with empty deck (and vector cards not used/exhausted)."
		);
	}

	// peek_next_card returns Option<Card>. Since num_available > 0, we expect Some.
	// This gets the next card in the deck's current (shuffled) order.
	let sampled_card: Card = state
		.deck
		.peek_next_card()
		.expect("Deck should have a card if num_available > 0");
	let sampled_action = ConcreteAction(sampled_card.standard_deck_index() as u64);
	let prob = 1.0 / num_available as Prob;
	// log::trace!("[sample_chance_action] Deck (pre-shuffled) peeked card: {:?}, action: {}, prob: {}", sampled_card, sampled_action.0, prob);
	Some((sampled_action, prob))
}

```

crates/games/src/hulh/state/infoset.rs:
```
//! Information set key calculation for HULH.

use super::core::HulhState;
use engine::types::{ConcreteAction, InfosetHashKey, PlayerId}; // Added ConcreteAction
use fastcards::card::Card;
use log;
use rustc_hash::FxHasher;
use std::hash::{Hash, Hasher};

/// Calculates the information state key for the given player.
pub(crate) fn calculate_infoset_key(state: &HulhState, player: PlayerId) -> InfosetHashKey {
	// Return sentinel key for invalid player index or before hole cards are dealt.
	if player >= state.num_players {
		log::trace!(
			"InfosetKey P{}: Returning sentinel (invalid player)",
			player
		);
		return InfosetHashKey(u64::MAX);
	}

	// NOTE: pending_oot logic removed.

	let mut hasher = FxHasher::default();

	// Check if player has pocket aces to determine if we should show detailed logging
	let player_cards: Vec<Card> = state.private_cards[player]
		.iter()
		.filter_map(|&c| c)
		.collect();
	
	let _has_pocket_aces = player_cards.len() == 2 && 
		player_cards.iter().all(|card| card.rank_index() == 12); // Ace is rank index 12
	
	// if has_pocket_aces {
	// 	println!("\n═══════════════════════════════════════════════════════════════════════════");
	// 	println!("🔑 INFOSET KEY CALCULATION for Player {} (POCKET ACES!)", player);
	// 	println!("═══════════════════════════════════════════════════════════════════════════");
	// }

	// 1. Private cards (sorted)
	let mut private_sorted: Vec<Card> = state.private_cards[player]
		.iter()
		.filter_map(|&c| c)
		.collect();
	private_sorted.sort_unstable();
	private_sorted.hash(&mut hasher);

	// 2. Public / board cards (sorted)
	let mut public_sorted: Vec<Card> = (0..state.board_cards_len as usize)
		.map(|i| state.board_cards[i])
		.collect();
	public_sorted.sort_unstable();
	public_sorted.hash(&mut hasher);

	// 3. Unified action history (deals and bets)
	// Iterate through history, censoring opponent hole cards.
	use crate::hulh::constants::BETTING_SEQ_SENTINEL;
	use engine::state::State; // Import the State trait to call history()
	use engine::types::CHANCE_PLAYER_ID; // A distinct placeholder

	// Placeholder for opponent's private card deals in the history hash.
	// Needs to be a ConcreteAction. Using a value unlikely to be a real card ID or betting action.
	const OPPONENT_HOLE_CARD_DEAL_PLACEHOLDER: ConcreteAction = BETTING_SEQ_SENTINEL;

	let mut hole_cards_dealt_in_history = 0;
	let total_hole_cards_to_be_dealt = state.num_players() * state.config_num_hole_cards;

	for (_i, (actor_id, concrete_action)) in state.history().iter().enumerate() {
		actor_id.hash(&mut hasher); // Hash who acted

		if *actor_id == CHANCE_PLAYER_ID {
			if hole_cards_dealt_in_history < total_hole_cards_to_be_dealt {
				// This is a hole card deal
				// Determine which player this card was for.
				// HULH deals all cards for P0, then all for P1, etc.
				let player_receiving_this_card =
					hole_cards_dealt_in_history / state.config_num_hole_cards;

				if player_receiving_this_card == player {
					concrete_action.hash(&mut hasher); // Player's own card, hash it
				} else {
					OPPONENT_HOLE_CARD_DEAL_PLACEHOLDER.hash(&mut hasher); // Opponent's card, hash placeholder
				}
				hole_cards_dealt_in_history += 1;
			} else {
				// This is a board card deal (public)
				concrete_action.hash(&mut hasher);
			}
		} else {
			// This is a player betting action
			concrete_action.hash(&mut hasher);
		}
	}

	// 4. Player to move (already included implicitly by history if history is correctly defined and processed)
	// Hashing explicitly for safety/clarity, especially if history processing changes.
	// but it doesn't hurt and ensures correctness if history representation changes.
	state.current_player.hash(&mut hasher);

	// 5. pending OOT (acts are public once announced) - REMOVED
	// state.pending_oot.hash(&mut hasher);

	// 6. Bucketed stacks for all non-folded players
	// This ensures similar stack sizes map to the same infoset
	use engine::globals::bucket_stack;
	for p in 0..state.num_players {
		if !state.folded[p] {
			let bucketed = bucket_stack(state.stacks[p]);
			bucketed.hash(&mut hasher);
		}
	}

	let final_key = InfosetHashKey(hasher.finish());
	
	final_key
}

```

crates/games/src/hulh/state/mod.rs:
```
//! Submodules defining the logic for HulhState.

pub(crate) mod betting;
pub mod core;
pub mod dealing; // Made public for bucketed_get_chance_outcomes
pub(crate) mod infoset;
pub(crate) mod round;
pub mod showdown; // Made public for test access to counter

// Re-export commonly used types
pub use self::core::BettingContext;

```

crates/games/src/hulh/state/round.rs:
```
//! Logic for handling betting round progression in HULH.

use super::core::HulhState;
use crate::hulh::constants::MAX_SEATS; // Import specific constants, remove BROKEN_FLOAT_TOLERANCE
use engine::types::{PlayerId, CHANCE_PLAYER_ID};
use log;
// abs_diff_eq removed

/// Determines the player to act next in the current betting round.
/// Handles SB/BB positions and skips folded or all-in players.
/// Correction: Skips only folded players. All-in players may still need to act (check).
pub(crate) fn next_betting_player(state: &HulhState, current_player: PlayerId) -> PlayerId {
	let mut next = (current_player + 1) % state.num_players;
	let mut loop_count = 0; // Safety break
						 // Skip seats that are folded OR all-in. All-in players cannot take further
						 // betting actions (they can only check if no bet is pending, which is
						 // handled within apply_bet/legal_actions, not by giving them the turn here).
	while state.folded[next] || state.all_in[next] {
		// Skip folded OR all-in players
		next = (next + 1) % state.num_players;
		if next == current_player || loop_count > state.num_players {
			log::warn!("[next_betting_player] Loop detected or completed full circle (folded/all-in), returning original player {}", current_player);
			return current_player; // Avoid infinite loop if all others folded
		}
		loop_count += 1;
	}
	// log::trace!("[next_betting_player] current={} -> next={}", current_player, next);
	next
}

/// Checks if the current betting round should end.
pub(crate) fn is_betting_round_over(state: &HulhState) -> bool {
	// Check if only one player (or fewer) remains *unfolded*. This is a game-ending condition.
	if state.remaining_players <= 1 {
		// log::debug!("IBRO: Round over (<= 1 unfolded player remaining)"); // Perf: Simple log, low impact
		return true;
	}

	let actions_this_round = state.betting_len[state.round] as usize;

	// Handle edge case: If no actions yet this round, it cannot be over.
	if actions_this_round == 0 {
		// log::debug!("IBRO: Round continues (no actions yet this round)"); // Perf: Simple log, low impact
		return false;
	}

	// Check if everyone still in the hand (not folded) has either matched the current stake or is all-in.
	// This is a necessary condition for the round to end.
	// Perf: players_not_matched vector and its usage removed for performance.
	// let mut players_not_matched = Vec::new(); // Store players who haven't matched
	let all_potentially_matched = (0..state.num_players)
		.filter(|&p| !state.folded[p]) // Consider all non-folded players
		.all(|p| state.all_in[p] || state.ante[p] == state.stakes); // Direct comparison for Chips

	if !all_potentially_matched {
		// If someone hasn't matched the current bet level (and isn't all-in), the round cannot be over.
		// Perf: Removed for performance. Formatting a vector with {:?} is expensive.
		// log::trace!("[IBRO] Round continues (not all players matched stakes={}). Unmatched: {:?}", state.stakes, players_not_matched);
		return false;
	}

	// everyone has matched the current stake (or is all-in)
	// -----------------------------------------------------
	// NEW: if ≤ 1 live seat still owns chips there cannot be further betting,
	// so the round ends right now and we move on to the next chance node.
	let active_with_chips = (0..state.num_players)
		.filter(|&p| !state.folded[p] && !state.all_in[p])
		.count();
	if active_with_chips <= 1 {
		// simple debug line – executes at most once per round
		// log::debug!("[IBRO] round over – only {} active stack(s) remain", active_with_chips); // Perf: Moderate impact, commented out as it's in a hot path.
		return true;
	}

	// Check if all active players are all-in.
	let active_players: Vec<PlayerId> = state.seats().filter(|&p| !state.folded[p]).collect();
	let all_active_are_all_in = active_players.iter().all(|&p| state.all_in[p]);

	if all_active_are_all_in && actions_this_round > 0 {
		// Ensure at least one action happened
		// Perf: Removed for performance. Formatting a vector with {:?} is expensive.
		// log::debug!("[IBRO] Round over (all active players {:?} are all-in)", active_players);
		return true;
	}

	// If we reach here, everyone not folded has matched the stakes or is all-in,
	// AND at least one active player is NOT all-in.
	match state.last_raiser {
		None => {
			// --- No bet/raise this round ---
			// The round ends *unless* it's pre-flop and the BB hasn't acted on their option yet.
			if state.round == 0 && !state.bb_checked_preflop {
				// log::debug!("IBRO: Round continues (pre-flop, BB option pending)"); // Perf: Simple log, low impact
				false
			} else {
				// No aggression – round ends once the action *returns* to
				// the original round starter.
				// This fixes a premature round-termination bug.

				// Starting seat for this betting round.
				let round_starter = if state.round == 0 {
					state.first_to_act_preflop()
				} else {
					state.first_to_act_postflop()
				};

				// Skip folded players to find the first active starter.
				let mut actual_starter = round_starter;
				while state.folded[actual_starter] || state.all_in[actual_starter] {
					actual_starter = (actual_starter + 1) % state.num_players;
				}

				// Who is up next?
				let next_player_to_act = next_betting_player(state, state.current_player);

				// Round ends when next actor returns to starter after at least one action.
				next_player_to_act == actual_starter && actions_this_round > 0
			}
		}
		Some(last_raiser_id) => {
			// --- Aggression occurred ---
			// Round ends if the action is back on the last aggressor.
			// Calculate the *next* player after the current one who can actually bet.
			let player_after_current = next_betting_player(state, state.current_player);

			// Check if the action has completed its circuit back to the raiser.
			// This happens if the next player to act *would be* the raiser.
			let end = player_after_current == last_raiser_id;

			// Handle cases where the raiser or intermediate players are all-in/folded.
			let mut round_should_end = end; // Start with the simple check

			// If the simple check fails, check if all players between the next actor
			// and the raiser are inactive (folded). All-in players might still check.
			if !round_should_end {
				let mut intermediate_player = player_after_current;
				let mut all_intermediate_inactive = true;
				let mut loop_guard = 0; // Prevent infinite loops in unexpected states

				// Loop from the player after current up to (but not including) the last raiser
				while intermediate_player != last_raiser_id && loop_guard <= state.num_players {
					// Check if this intermediate player is folded
					if !state.folded[intermediate_player] {
						// If an intermediate player is not folded, they might still act (e.g., check if all-in).
						// However, if the action truly passed them and landed back at the raiser,
						// it implies they must have checked/called. The simple `end` check covers this.
						// This enhanced check primarily handles cases where *everyone* between
						// the current player and the raiser is folded.
						all_intermediate_inactive = false;
						break; // Found a non-folded player, rely on simple `end` check.
					}
					intermediate_player = (intermediate_player + 1) % state.num_players;
					loop_guard += 1;
				}
				// If all players between the next actor and the raiser are inactive, the round ends.
				if all_intermediate_inactive {
					round_should_end = true;
				}
			}
			// Perf: This log involves multiple arguments and formatting, can be costly in a hot path.
			// log::trace!("[IBRO Aggression Final] Round over check result: (player_after_current={}, last_raiser={}, simple_end={}, final_end={})",
			//           player_after_current, last_raiser_id, end, round_should_end);
			round_should_end
		}
	}
}

/// Starts the next round (Flop, Turn, or River).
pub(crate) fn start_next_round(state: &mut HulhState) {
	// log::trace!("Starting next round (Current Round {})", state.round);
	state.round += 1;
	state.num_raises = 0;
	state.stakes = 0; // Reset stakes for the new round
	state.ante = [0; MAX_SEATS];
	state.betting_len[state.round] = 0; // Reset betting counter for the new round
	state.last_raiser = None;
	state.cards_dealt_this_round = 0; // Reset card dealing counter
	state.last_bet_or_raise_increment = 0; // Reset for new betting rules
	state.current_player = CHANCE_PLAYER_ID; // Deal community cards
	state.clear_round_local_flags();

	// log::trace!("start_next_round finished. New Round={}, Player={}", state.round, state.current_player);
}

```

crates/games/src/hulh/state/showdown.rs:
```
//! Logic for handling showdown and calculating returns in HULH.

use super::core::{HulhState, Pot}; // Import Pot struct
use crate::hulh::{
	constants::{MAX_BOARD_CARDS, MAX_SEATS}, // Import specific constants, remove BROKEN_FLOAT_TOLERANCE
	settings::DeckType,                      // Import DeckType
};
use crate::Chips; // Use Chips from crate root
use engine::state::State;
use engine::types::{PlayerId, Utility, TERMINAL_PLAYER_ID}; // Keep engine types
use fastcards::{
	eval::best_five_of_seven,
	HandRank,
};
use log;
use smallvec::SmallVec;
// Removed unused imports: use std::sync::atomic::{AtomicUsize, Ordering};
#[cfg(debug_assertions)]
use std::sync::atomic::Ordering; // Conditionally compile the import

#[cfg(debug_assertions)]
pub static DEBUG_HAND_EVAL_COUNT: std::sync::atomic::AtomicUsize =
	std::sync::atomic::AtomicUsize::new(0);
#[cfg(debug_assertions)]
pub static DEBUG_HAND_EVAL_CACHE_HITS: std::sync::atomic::AtomicUsize =
	std::sync::atomic::AtomicUsize::new(0);

#[cfg(debug_assertions)]
pub fn reset_debug_hand_eval_count() {
	DEBUG_HAND_EVAL_COUNT.store(0, std::sync::atomic::Ordering::SeqCst);
}

#[cfg(debug_assertions)]
pub fn reset_debug_hand_eval_cache_hits() {
	DEBUG_HAND_EVAL_CACHE_HITS.store(0, std::sync::atomic::Ordering::SeqCst);
}

/// Builds the main and side pots based on player contributions and folded status.
/// Returns a vector of pots, where pots[0] is the main pot.
pub(crate) fn build_side_pots(
	num_players: usize,
	total_contribution: &[Chips; MAX_SEATS],
	folded: &[bool; MAX_SEATS],
) -> SmallVec<[Pot; MAX_SEATS + 1]> {
	log::trace!(
	    "[build_side_pots_ENTRY] num_players={}, total_contribution={:?}, folded={:?}",
	    num_players,
	    &total_contribution[..num_players],
	    &folded[..num_players]
	);

	let mut pots: SmallVec<[Pot; MAX_SEATS + 1]> = SmallVec::new();

	// 1. Get unique, sorted, non-zero contribution levels
	let mut unique_levels: Vec<Chips> = total_contribution[..num_players]
		.iter()
		.filter(|&&c| c > 0) // Filter non-zero contributions
		.copied()
		.collect();
	// Sort and deduplicate Chips
	unique_levels.sort_unstable();
	unique_levels.dedup();

	let mut last_level = 0;

	// 2. Loop through levels to create pot slices
	for current_level in unique_levels {
		let slice_amount = current_level - last_level;

		if slice_amount == 0 {
			last_level = current_level; // Still update last_level
			continue;
		}

		let mut current_pot_amount = 0;
		let mut current_contenders: SmallVec<[PlayerId; MAX_SEATS]> = SmallVec::new();

		// 3. Collect contributions for this slice from all players
		for p in 0..num_players {
			// Amount this player contributes *to this specific pot slice*
			// Player must have contributed at least up to the previous level to be part of this slice.
			let contrib_this_slice = if total_contribution[p] > last_level {
				(total_contribution[p] - last_level).min(slice_amount)
			} else {
				0
			};

			if contrib_this_slice > 0 {
				current_pot_amount += contrib_this_slice;

				// Add player to contenders if they haven't folded
				if !folded[p] {
					// Check if contender already added (shouldn't happen with this logic, but safe)
					if !current_contenders.contains(&p) {
						current_contenders.push(p);
					}
				}
			}
		}

		// 4. Push a new pot for this slice if it has value
		if current_pot_amount > 0 {
			current_contenders.sort_unstable(); // Keep contenders sorted
									   log::trace!(
									       "[build_side_pots_LOOP] current_level={}, slice_amount={}, calculated_pot_amount={}, contenders={:?}",
									       current_level,
									       slice_amount,
									       current_pot_amount,
									       current_contenders
									   );
			pots.push(Pot {
				amount: current_pot_amount,
				contenders: current_contenders,
				// winners field removed
			});
		}

		last_level = current_level; // Update the level for the next iteration
	}

	// Ensure at least a main pot exists, even if empty (e.g., everyone folds pre-flop)
	if pots.is_empty() {
		pots.push(Pot {
			amount: 0,
			contenders: SmallVec::new(),
			// winners field removed
		});
	}

	pots
}

/**
 * Evaluates hands at showdown and determines the winner(s) for each pot.
 *
 * Updates `state.pots` with amounts and contenders, and determines winners per pot.
 *
 * Note: As of Phase 5, this function may be called automatically by
 * `dealing::deal_card` when both players are all-in and the river has been dealt.
 */
pub(crate) fn resolve_showdown(state: &mut HulhState) {
	log::trace!(
		"[RESOLVE_SHOWDOWN_ENTRY] Called. Round: {}, Player: {:?}, Winner: {:?}, Board (len {}): {:?}",
		state.round,
		state.current_player,
		state.winner,
		state.board_cards_len,
		&state.board_cards[..state.board_cards_len as usize]
	);
	if state.winner.is_some() {
		log::trace!(" -> Already resolved (Winner: {:?})", state.winner);
		return;
	}

	if state.remaining_players == 1 {
		if let Some(p) = state.seats().find(|&p| !state.folded[p]) {
			state.winner = Some(p);
			log::trace!(" -> Winner by fold: P{}", p);
			// No hand evaluation needed, cache remains as is or empty.
			// board_len_for_eval_cache is not set here as no eval happened for this board.
		} else {
			log::error!("Showdown: remaining_players is 1 but no winner found. This indicates an inconsistent state.");
			state.winner = None;
		}
	} else {
		// --- Actual Showdown: Evaluate Hands ---
		let mut evaluated_ranks_for_overall_winner: Vec<(PlayerId, HandRank)> =
			Vec::with_capacity(state.remaining_players);
		let board_cards_fc: [fastcards::card::Card; MAX_BOARD_CARDS] = state.board_cards;

		match state.config_deck_type {
			DeckType::Standard52 | DeckType::ShortDeck36 => {
				log::trace!("Performing standard Hold'em showdown evaluation.");
				if state.board_cards_len < MAX_BOARD_CARDS as u8 {
					// Standard Hold'em expects 5 board cards for full eval
					log::warn!(
						"Showdown called with incomplete board ({} cards). Proceeding.",
						state.board_cards_len
					);
				}

				for p in state.seats() {
					if !state.folded[p] {
						log::trace!("[RESOLVE_SHOWDOWN_CACHE_CHECK_PLAYER P{}] config_vector_cards={}, evaluated_hands[p]={:?}, private_cards[p]={:?}/{:?}, board_len={}",
						p, state.config_vector_cards, state.evaluated_hands[p], state.private_cards[p][0], state.private_cards[p][1], state.board_cards_len);
						if state.config_vector_cards && state.evaluated_hands[p].is_some() {
							#[cfg(debug_assertions)]
							{
								DEBUG_HAND_EVAL_CACHE_HITS.fetch_add(1, Ordering::SeqCst);
							}
							let rank = state.evaluated_hands[p].unwrap();
							evaluated_ranks_for_overall_winner.push((p, rank));
							log::trace!(" -> P{} Hold'em rank from cache: {:?}. Board: {:?}, Private: {:?}/{:?}", p, rank, &board_cards_fc[..state.board_cards_len as usize], state.private_cards[p][0], state.private_cards[p][1]);
						} else if let (Some(hc1), Some(hc2)) =
							(state.private_cards[p][0], state.private_cards[p][1])
						{
							#[cfg(debug_assertions)]
							{
								DEBUG_HAND_EVAL_COUNT.fetch_add(1, Ordering::SeqCst);
							}
							let rank = best_five_of_seven(
								hc1,
								hc2,
								board_cards_fc[0],
								board_cards_fc[1],
								board_cards_fc[2],
								board_cards_fc[3],
								board_cards_fc[4], // These might be Card(0) if board_cards_len < 5
							);

							state.evaluated_hands[p] = Some(rank);
							evaluated_ranks_for_overall_winner.push((p, rank));
							log::trace!(" -> P{} Hold'em rank EVALUATED: {:?}. Board: {:?}, Private: {:?}/{:?}", p, rank, &board_cards_fc[..state.board_cards_len as usize], hc1, hc2);
						} else {
							log::error!(
								"Player {} not folded but missing hole cards at Hold'em showdown.",
								p
							);
							state.evaluated_hands[p] = None;
						}
					}
				}
				if !evaluated_ranks_for_overall_winner.is_empty() {
					evaluated_ranks_for_overall_winner.sort_unstable_by(|a, b| a.1.cmp(&b.1)); // Lower HandRank is better
					state.winner = Some(evaluated_ranks_for_overall_winner[0].0);
					log::trace!(" -> Hold'em Showdown complete. Overall best hand by P{}: {:?}", state.winner.unwrap(), evaluated_ranks_for_overall_winner[0].1);
				} else {
					log::error!("Hold'em Showdown: No hands were evaluated.");
					state.winner = None;
				}
			}
		}
	}

	state.current_player = TERMINAL_PLAYER_ID;
	log::trace!(" -> Showdown resolved. Overall Winner: {:?}, CurrentPlayer: {}", state.winner, state.current_player);
}

/// Calculates the final returns for each player based on pot distribution.
/// This function now handles the full pot building and winner determination logic.
pub(crate) fn calculate_returns(state: &HulhState) -> Vec<Utility> {
	if !state.is_terminal() {
		log::warn!(
			"calculate_returns called on non-terminal state. Player: {}, Winner: {:?}",
			state.current_player,
			state.winner
		);
		// It's possible for this to be called by to_string() on a non-terminal state for debug display.
		// Let's not panic here, but return what would be the current losses.
		let mut returns = vec![0.0; state.num_players];
		for p in state.seats() {
			returns[p] = -(state.total_contribution[p] as Utility);
		}
		return returns;
		// panic!("calculate_returns called on non-terminal state. Player: {}, Winner: {:?}", state.current_player, state.winner);
	}

	// Returns are still Utility (f64) as per the State trait definition.
	let mut returns = vec![0.0; state.num_players];

	// Initialize returns: everyone loses what they contributed initially.
	for p in state.seats() {
		// Convert Chips contribution to Utility loss
		returns[p] = -(state.total_contribution[p] as Utility);
	}

	// 1. Build the side pots based on final contributions and folded status.
	let pots_at_showdown =
		build_side_pots(state.num_players, &state.total_contribution, &state.folded);
	log::trace!("[calculate_returns] Built pots: {:?}", pots_at_showdown);

	// 2. Determine winners and distribute winnings for each pot on the fly.
	let mut total_dead_money = 0; // Use Chips for dead money tracking

	for pot in pots_at_showdown.iter() {
		if pot.amount == 0 {
			continue; // Skip empty pots
		}
		if pot.contenders.is_empty() {
			total_dead_money += pot.amount;
			log::trace!(" -> Pot amount {}, Contenders EMPTY (Dead Money)", pot.amount);
			continue; // Skip pots with no contenders (already accounted for as dead money)
		}

		let mut current_pot_winners: SmallVec<[PlayerId; MAX_SEATS]> = SmallVec::new();

		if state.remaining_players == 1 {
			// --- Win by fold ---
			if let Some(sole_winner_id) = state.winner {
				if pot.contenders.contains(&sole_winner_id) {
					current_pot_winners.push(sole_winner_id);
				}
			} else {
				panic!("[calculate_returns] Inconsistent state: remaining_players is 1, but state.winner is None.");
			}
		} else {
			// --- Actual Showdown ---
			// Use evaluated_hands which now contains either HandRank (Hold'em) or RankIndex (Leduc)
			let mut best_rank_in_pot: Option<HandRank> = None; // Use HandRank (u16) for comparison

			for &contender_id in &pot.contenders {
				if let Some(rank) = state.evaluated_hands[contender_id] {
					// rank is u16
					// Comparison logic depends on game type implicitly stored in rank values
					// For Hold'em: lower rank is better.
					// Here, we just need to find all players matching the best rank found for this pot.

					// Find the best rank value among contenders for this pot
					// Lower rank is better for HandRank
					if best_rank_in_pot.is_none() || rank < best_rank_in_pot.unwrap() {
						best_rank_in_pot = Some(rank);
					}
				} else {
					panic!(
						"[calculate_returns] Pot contender P{} has no evaluated hand.",
						contender_id
					);
				}
			}

			// Find all contenders matching the best rank for this pot
			if let Some(best_rank) = best_rank_in_pot {
				for &contender_id in &pot.contenders {
					if let Some(rank) = state.evaluated_hands[contender_id] {
						if rank == best_rank {
							current_pot_winners.push(contender_id);
						}
					}
				}
			}
			// If best_rank_in_pot remained None (e.g., all contenders had no evaluated hand), current_pot_winners will be empty.
		}

		// --- Distribute Winnings for this Pot ---
		if current_pot_winners.is_empty() {
			// No winners for this pot (e.g., all contenders folded or had no hand)
			total_dead_money += pot.amount;
			log::trace!(" -> Pot amount {}, Contenders {:?}, Winners: NONE (Dead Money)", pot.amount, pot.contenders);
			continue; // Move to the next pot
		}

		log::trace!(" -> Pot amount {}, Contenders {:?}, Winners: {:?}", pot.amount, pot.contenders, current_pot_winners);

		let num_winners = current_pot_winners.len();
		let base_share = pot.amount / num_winners as Chips; // Integer division
		let odd_chips = pot.amount % num_winners as Chips; // Remainder for odd chips

		for &winner_id in &current_pot_winners {
			if winner_id < state.num_players {
				// Bounds check
				returns[winner_id] += base_share as Utility; // Add base share as Utility
			}
		}

		// Distribute odd chips (if any) starting left of the button among winners
		if odd_chips > 0 {
			let mut chips_to_distribute = odd_chips;
			let mut odd_chip_receiver_found = false; // Flag to ensure only one loop if needed
			for i in 0..state.num_players {
				if chips_to_distribute == 0 {
					break;
				} // All odd chips distributed
				let seat_to_check = (state.dealer_btn + 1 + i) % state.num_players;
				if current_pot_winners.contains(&seat_to_check) && seat_to_check < state.num_players
				{
					// Bounds check
					returns[seat_to_check] += 1.0; // Add one chip as Utility
					chips_to_distribute -= 1;
					odd_chip_receiver_found = true; // Mark that we found at least one winner
					                 log::trace!("[calculate_returns] P{} receives 1 odd chip for pot amount {}", seat_to_check, pot.amount);
				}
			}
			// Fallback if loop completes without distributing all chips (shouldn't happen if winners exist)
			if chips_to_distribute > 0
				&& !odd_chip_receiver_found
				&& !current_pot_winners.is_empty()
			{
				log::warn!("[calculate_returns] Odd chip distribution fallback needed for pot amount {}. Winners: {:?}. Remaining odd chips: {}", pot.amount, current_pot_winners, chips_to_distribute);
				// Distribute remaining chips to the first winner in the list as a fallback
				if let Some(&first_winner) = current_pot_winners.first() {
					if first_winner < state.num_players {
						returns[first_winner] += chips_to_distribute as Utility;
					}
				}
			}
		}
	} // End loop over pots

	// Final sanity check: returns should sum to zero, *unless* there's dead money
	let sum_of_returns: Utility = returns.iter().sum();
	// Use the locally calculated total_dead_money (convert to Utility for comparison)
	let dead_money_utility = total_dead_money as Utility;
	if (sum_of_returns + dead_money_utility).abs() > 1e-5 {
		// Use tolerance for Utility sum check
		log::error!(
            "Returns sum ({:.6}) + Dead Money ({}) does not equal zero: {:.6}. Contributions: {:?}, Pots built: {:?}, Evaluated Hands: {:?}",
            sum_of_returns, total_dead_money, sum_of_returns + dead_money_utility,
            &state.total_contribution[..state.num_players],
            pots_at_showdown, // Keep showing the built pots structure for context
            &state.evaluated_hands[..state.num_players]
        );
		// debug_assert is fine here, but error log helps in release if it ever happens.
	}
	debug_assert!(
		(sum_of_returns + dead_money_utility).abs() < 1e-5,
		"Returns sum ({:.6}) + Dead Money ({}) != 0: {:.6}. Contrib: {:?}, Pots: {:?}, Hands: {:?}",
		sum_of_returns,
		total_dead_money,
		sum_of_returns + dead_money_utility,
		&state.total_contribution[..state.num_players],
		pots_at_showdown, // Keep showing the built pots structure for context
		&state.evaluated_hands[..state.num_players]
	);

	log::trace!("[calculate_returns] Returns: {:?}", returns);

	returns
}

```

crates/games/src/hulh/undo.rs:
```
//! Defines the UndoRecord structure for HULH state reversal.

use crate::hulh::constants::MAX_SEATS; // Import specific constant
use crate::Chips; // Use Chips from crate root
use engine::types::PlayerId; // Keep engine types needed
use fastcards::{card::Card, HandRank};
// Removed unused imports:
// use smallvec::SmallVec;
// use crate::hulh::state::core::Pot;

// --- Undo Record ---

#[derive(Debug, Clone)]
pub struct PreRoundState {
	// Changed to pub
	pub(crate) round: usize,
	pub(crate) _num_raises: usize, // Prefixed: Not read in undo_bet
	pub(crate) _stakes: Chips,     // Prefixed: Not read in undo_bet
	pub(crate) ante: [Chips; MAX_SEATS],
	pub(crate) _last_raiser: Option<PlayerId>, // Prefixed: Not read in undo_bet
	// Player ID *before* the transition to CHANCE
	pub(crate) _player_before_deal: PlayerId, // Prefixed: Not read in undo_bet
	pub(crate) cards_dealt_this_round: usize,
	pub(crate) _last_bet_or_raise_increment: Chips, // Prefixed: Not read in undo_bet
}

#[derive(Debug, Clone)]
pub struct PreResolveState {
	// Changed to pub
	pub(crate) winner: Option<PlayerId>,
	pub(crate) evaluated_hands: [Option<HandRank>; MAX_SEATS],
	// Player ID *before* setting to TERMINAL
	pub(crate) _player_before_terminal: PlayerId, // Prefixed: Not read in undo_bet
}

#[allow(clippy::large_enum_variant)]
#[derive(Debug, Clone)]
pub enum UndoRecord {
	// Changed to pub
	DealPrivate {
		player: PlayerId,
		card_pos: usize,
		card: Card,            // The card that was revealed
		prev_player: PlayerId, // Player ID before this deal action
	},
	DealPublic {
		card: Card,
		prev_player: PlayerId, // Player ID before this deal action
	},
	Bet {
		move_type: super::action::HulhMove,
		// --- Core Bet Undo Info ---
		player: PlayerId, // Player who acted
		// Values *before* the bet action
		prev_stakes: Chips,
		prev_pot: Chips,
		prev_ante: Chips,
		prev_total_contribution: Chips,
		prev_num_raises: usize,
		prev_last_raiser: Option<PlayerId>,
		prev_bb_checked_preflop: bool,
		// State changes caused by the bet
		was_folded: bool,
		// Player ID *before* this betting action
		prev_player: PlayerId,
		// Phase 4 additions (use ConcreteAction)
		// prev_pending_oot removed
		prev_saw_forward_motion: bool,
		prev_last_bet_or_raise_increment: Chips, // Added field

		// --- Optional Transition Undo Info ---
		// Store state *before* the transition occurred
		round_transition_state: Option<PreRoundState>,
		resolve_transition_state: Option<PreResolveState>,
	},
}

```

crates/games/src/hulh/utils.rs:
```
//! Utility functions for HULH.

use crate::hulh::settings::{HulhSettings, RaiseRuleType};
use crate::Chips;


/// Calculates the maximum possible commitment a single player can make in a hand.
/// This considers all betting rules and settings.
pub fn calculate_max_commitment(settings: &HulhSettings) -> Chips {
	// Start with the ante, as this is a mandatory contribution if > 0.
	let mut max_player_total_contribution_in_hand = settings.ante;

	for round_idx in 0..settings.num_rounds {
		let mut player_chips_invested_this_round: Chips = 0;
		// current_round_bet_target is the amount a player must have invested in this round to call.
		let mut current_round_bet_target: Chips = 0;
		let mut last_bet_or_raise_increment_for_calc: Chips = 0;

		// If it's the first round and there's a big blind, player (as BB or caller) contributes it.
		if round_idx == 0 && settings.big_blind > 0 {
			player_chips_invested_this_round = settings.big_blind;
			current_round_bet_target = settings.big_blind;
			last_bet_or_raise_increment_for_calc = settings.big_blind;
		}

		let num_bets_allowed_this_round = settings.max_raises.get(round_idx).copied().unwrap_or(0);

		for bet_action_idx in 0..num_bets_allowed_this_round {
			let mut current_bet_or_raise_action_size: Chips;

			// Determine the size of the current bet or raise action
			if bet_action_idx == 0 && current_round_bet_target == 0 {
				// This is an opening bet
				current_bet_or_raise_action_size = settings
					.opening_bet_sizes
					.get(round_idx)
					.and_then(|sizes| sizes.iter().max().copied())
					.unwrap_or_else(|| {
						settings
							.fixed_raise_amounts
							.get(round_idx)
							.copied()
							.unwrap_or(0)
					});

				// Fallback if opening_bet_sizes are zero/empty but fixed_raise_amounts are not
				if current_bet_or_raise_action_size == 0 {
					if let Some(&fixed_amount) = settings.fixed_raise_amounts.get(round_idx) {
						if fixed_amount > 0 {
							current_bet_or_raise_action_size = fixed_amount;
						}
					}
				}
			} else {
				// This is a raise over an existing bet (or BB)
				match settings.raise_rule {
					RaiseRuleType::FixedAmount => {
						current_bet_or_raise_action_size = settings
							.fixed_raise_amounts
							.get(round_idx)
							.copied()
							.unwrap_or(0);
					}
					RaiseRuleType::DoublePreviousBetOrRaise
					| RaiseRuleType::MatchPreviousBetOrRaise => {
						if last_bet_or_raise_increment_for_calc > 0 {
							current_bet_or_raise_action_size =
								if settings.raise_rule == RaiseRuleType::DoublePreviousBetOrRaise {
									last_bet_or_raise_increment_for_calc * 2
								} else {
									// MatchPreviousBetOrRaise
									last_bet_or_raise_increment_for_calc
								};
						} else {
							// No previous bet/raise to base dynamic raise on; treat as an opening bet
							current_bet_or_raise_action_size = settings
								.opening_bet_sizes
								.get(round_idx)
								.and_then(|sizes| sizes.iter().max().copied())
								.unwrap_or_else(|| {
									settings
										.fixed_raise_amounts
										.get(round_idx)
										.copied()
										.unwrap_or(0)
								});
							if current_bet_or_raise_action_size == 0 {
								// Fallback
								if let Some(&fixed_amount) =
									settings.fixed_raise_amounts.get(round_idx)
								{
									if fixed_amount > 0 {
										current_bet_or_raise_action_size = fixed_amount;
									}
								}
							}
						}
					}
				}
			}

			if current_bet_or_raise_action_size == 0 {
				// No effective bet/raise possible
				break; // Stop betting for this round
			}

			// Calculate chips this player adds in this action:
			// They must call up to current_round_bet_target, then add current_bet_or_raise_action_size.
			let chips_to_add_for_this_action = current_round_bet_target
				.saturating_sub(player_chips_invested_this_round)
				+ current_bet_or_raise_action_size;

			player_chips_invested_this_round += chips_to_add_for_this_action;
			current_round_bet_target += current_bet_or_raise_action_size; // New target for others to call
			last_bet_or_raise_increment_for_calc = current_bet_or_raise_action_size;

			// Check if player would be all-in with this round's contribution
			if max_player_total_contribution_in_hand + player_chips_invested_this_round
				>= settings.starting_stack + settings.ante
			{
				let remaining_stack_before_this_round_contrib = (settings.starting_stack
					+ settings.ante)
					.saturating_sub(max_player_total_contribution_in_hand);
				player_chips_invested_this_round =
					player_chips_invested_this_round.min(remaining_stack_before_this_round_contrib);
				// max_player_total_contribution_in_hand will be updated after this inner loop, then capped.
				// This break signifies the player is all-in for this round.
				break;
			}
		}
		max_player_total_contribution_in_hand += player_chips_invested_this_round;

		// If player is all-in after this round, no more contributions possible in subsequent rounds.
		if max_player_total_contribution_in_hand >= settings.starting_stack + settings.ante {
			max_player_total_contribution_in_hand = settings.starting_stack + settings.ante;
			break; // Break from iterating over rounds
		}
	}
	// Final cap by starting stack (ante is already included in max_player_total_contribution_in_hand at this point)
	max_player_total_contribution_in_hand.min(settings.starting_stack + settings.ante)
}

```

crates/games/src/leduc/action.rs:
```
//! Leduc poker actions - simplified betting actions

use engine::types::ConcreteAction;

#[repr(u32)]
#[derive(Copy, Clone, Debug, Eq, PartialEq, Hash)]
/// Betting actions for Leduc poker.
///
/// Leduc uses the same overloaded CALL action as HULH:
/// - When facing a bet: CALL matches the current bet
/// - When NOT facing a bet: CALL contributes 0 (check)
pub enum LeducAction {
    Fold = 0,
    Call = 1,  // Overloaded: matches current stakes (0 if no bet)
    Raise = 2, // Fixed raise amount: 2 chips in round 0, 4 chips in round 1
}

impl From<LeducAction> for ConcreteAction {
    #[inline]
    fn from(a: LeducAction) -> Self {
        ConcreteAction(a as u64)
    }
}

// Action constants
pub const FOLD_ACTION: ConcreteAction = ConcreteAction(LeducAction::Fold as u64);
pub const CALL_ACTION: ConcreteAction = ConcreteAction(LeducAction::Call as u64);
pub const RAISE_ACTION: ConcreteAction = ConcreteAction(LeducAction::Raise as u64);

/// All possible Leduc actions
pub const LEDUC_ACTIONS: [ConcreteAction; 3] = [FOLD_ACTION, CALL_ACTION, RAISE_ACTION];

/// Convert a ConcreteAction to LeducAction
#[inline]
pub fn concrete_to_leduc(action: ConcreteAction) -> Option<LeducAction> {
    match action.0 {
        0 => Some(LeducAction::Fold),
        1 => Some(LeducAction::Call),
        2 => Some(LeducAction::Raise),
        _ => None,
    }
}

/// Get human-readable action string
pub fn action_string(action: LeducAction, is_facing_bet: bool) -> &'static str {
    match action {
        LeducAction::Fold => "Fold",
        LeducAction::Call => if is_facing_bet { "Call" } else { "Check" },
        LeducAction::Raise => if is_facing_bet { "Raise" } else { "Bet" },
    }
}
```

crates/games/src/leduc/constants.rs:
```
//! Leduc poker constants - simplified 6-card poker variant

use engine::types::{ConcreteAction, PlayerId};
use crate::Chips;

// Game structure constants
pub const NUM_PLAYERS: usize = 2;
pub const DECK_SIZE: usize = 6; // 6 cards total (J,Q,K of Spades,Hearts from ORDERED_LEDUC_FAST_DECK)
pub const NUM_ROUNDS: usize = 2; // Round 0: 1 hole card dealt, Round 1: 1 community card dealt
pub const NUM_HOLE_CARDS: usize = 1;
pub const NUM_COMMUNITY_CARDS: usize = 1;
pub const MAX_CARDS: usize = 2; // 1 hole + 1 community

// Betting structure
pub const ANTE: Chips = 1;
pub const STARTING_STACK: Chips = 100;

// Betting limits per round
pub const ROUND_BET_SIZES: [Chips; NUM_ROUNDS] = [2, 4]; // Round 0: 2 chips, Round 1: 4 chips
pub const MAX_RAISES_PER_ROUND: [usize; NUM_ROUNDS] = [2, 2]; // Max 2 raises per round

// Maximum actions in a round: check + bet + raise + re-raise + call = 5
// Being conservative for edge cases
pub const MAX_ACTIONS_PER_ROUND: usize = 8;

// Sentinel value for betting sequence initialization
pub const BETTING_SEQ_SENTINEL: ConcreteAction = ConcreteAction(u64::MAX - 1);

// Position-aware functions for Leduc
// Note: In canonical Leduc poker, non-dealer acts first in all betting rounds
// This matches academic papers (NIPS-2015 RBP, etc.) and standard implementations
#[inline]
pub const fn first_to_act(_round: usize, _num_players: usize) -> PlayerId {
    0
}

#[inline]
pub const fn second_to_act(_num_players: usize) -> PlayerId {
    1
}
```

crates/games/src/leduc/game.rs:
```
//! Leduc poker game implementation

use crate::leduc::{
    constants::NUM_PLAYERS,
    settings::LeducSettings,
    state::core::LeducState,
    utils,
};
use engine::{
    game::Game,
    position_context::get_position_context,
    types::Utility,
};
use cfr_rng::CfrRngPool;

/// Leduc poker game
#[derive(Debug, Clone)]
pub struct LeducGame {
    settings: LeducSettings,
    cached_min_utility: Utility,
    cached_max_utility: Utility,
}

impl LeducGame {
    /// Creates a new Leduc game with default settings
    pub fn new() -> Self {
        Self::new_with_settings(LeducSettings::default())
    }

    /// Creates a new Leduc game with specified settings
    pub fn new_with_settings(settings: LeducSettings) -> Self {
        assert_eq!(settings.num_players, NUM_PLAYERS, "Leduc only supports 2 players");
        
        let max_commit = utils::calculate_max_commitment(&settings);
        let min_util = -(max_commit as Utility);
        let max_util = max_commit as Utility; // Zero-sum game
        
        Self {
            settings,
            cached_min_utility: min_util,
            cached_max_utility: max_util,
        }
    }
}

impl Game for LeducGame {
    type State = LeducState;
    type Settings = LeducSettings;

    fn new_initial_state(&self, rng_pool: &mut CfrRngPool) -> Self::State {
        // Get dealer button from position context and convert to player ID
        let dealer_player = if let Some(mapping) = get_position_context() {
            let dealer_seat = mapping.dealer_button();
            log::trace!("Creating Leduc initial state with position mapping: dealer seat {}", dealer_seat);
            
            // Convert seat number to player ID using the mapping
            // This is critical: dealer_button() returns a seat index (0 or 1)
            // but we need the PlayerId of whoever is sitting at that seat
            let dealer_player_id = mapping.seat_to_player(engine::position::SeatNumber::from(dealer_seat));
            log::trace!("Dealer seat {} -> Player ID {}", dealer_seat, dealer_player_id);
            
            dealer_player_id
        } else {
            // PANIC to prevent position bias - position context is required
            panic!(
                "Creating Leduc state without position context - this would introduce position bias! \
                You must use PositionFair wrapper or set position context explicitly."
            );
        };
        
        LeducState::new(self, dealer_player, rng_pool)
    }

    fn num_players(&self) -> usize {
        self.settings.num_players
    }

    fn settings(&self) -> &Self::Settings {
        &self.settings
    }

    fn rules_summary(&self) -> String {
        format!(
            "Leduc Poker (2-player, Ante={}, Bet sizes={:?}, Stack={})",
            self.settings.ante,
            self.settings.bet_sizes,
            self.settings.starting_stack
        )
    }

    fn max_utility(&self) -> Utility {
        self.cached_max_utility
    }

    fn min_utility(&self) -> Utility {
        self.cached_min_utility
    }

    fn utility_sum(&self) -> Utility {
        0.0 // Zero-sum game
    }
}

impl Default for LeducGame {
    fn default() -> Self {
        Self::new()
    }
}
```

crates/games/src/leduc/mod.rs:
```
//! Leduc poker - a simplified 6-card poker variant

pub mod action;
pub mod constants;
pub mod game;
pub mod settings;
pub mod state;
pub mod undo;
pub mod utils;

// Public exports for easy access
pub use action::{LeducAction, CALL_ACTION, FOLD_ACTION, RAISE_ACTION};
pub use game::LeducGame;
pub use settings::LeducSettings;
pub use state::core::LeducState;

// Fixed positioning helpers - Leduc always has dealer acting first
pub use constants::{first_to_act, second_to_act};
```

crates/games/src/leduc/settings.rs:
```
//! Leduc poker settings - configuration for the simplified 6-card variant

use crate::Chips;
use engine::settings::GameSettings;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Configuration settings for Leduc poker
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LeducSettings {
    pub name: String,
    pub num_players: usize,      // Always 2 for Leduc
    pub num_rounds: usize,       // Always 2 for Leduc
    pub num_hole_cards: usize,   // Always 1 for Leduc
    pub ante: Chips,             // Ante amount (1 chip)
    pub bet_sizes: Vec<Chips>,   // Bet amounts per round [2, 4]
    pub max_raises: Vec<usize>,  // Max raises per round [2, 2]
    pub starting_stack: Chips,   // Starting chips per player
}

impl Default for LeducSettings {
    fn default() -> Self {
        LeducSettings {
            name: "Leduc".to_string(),
            num_players: 2,
            num_rounds: 2,
            num_hole_cards: 1,
            ante: 1,
            bet_sizes: vec![2, 4],      // Round 0: 2 chips, Round 1: 4 chips
            max_raises: vec![2, 2],     // Max 2 raises per round
            starting_stack: 100,
        }
    }
}

impl GameSettings for LeducSettings {
    fn to_key_value(&self) -> HashMap<String, String> {
        let mut map = HashMap::new();
        map.insert("game".to_string(), "leduc".to_string());
        map.insert("players".to_string(), self.num_players.to_string());
        map.insert("num_rounds".to_string(), self.num_rounds.to_string());
        map.insert("num_hole_cards".to_string(), self.num_hole_cards.to_string());
        map.insert("ante".to_string(), self.ante.to_string());
        map.insert(
            "bet_sizes".to_string(),
            self.bet_sizes
                .iter()
                .map(|x| x.to_string())
                .collect::<Vec<String>>()
                .join(","),
        );
        map.insert(
            "max_raises".to_string(),
            self.max_raises
                .iter()
                .map(|x| x.to_string())
                .collect::<Vec<String>>()
                .join(","),
        );
        map.insert("starting_stack".to_string(), self.starting_stack.to_string());
        map
    }

    fn get_game_name(&self) -> String {
        self.name.clone()
    }
}


```

crates/games/src/leduc/state/action_mapping.rs:
```
//! Action mapping for stable ES-CFR indexing
//! 
//! ES-CFR requires that actions always map to the same indices for proper
//! regret accumulation. This module provides the mapping between legal actions
//! and their stable indices.

use crate::leduc::action::{FOLD_ACTION, CALL_ACTION, RAISE_ACTION};
use engine::types::ConcreteAction;

/// Maximum number of actions in Leduc (FOLD, CALL, RAISE)
pub const MAX_LEDUC_ACTIONS: usize = 3;

/// Get the stable index for an action
/// This ensures consistent indexing for ES-CFR:
/// - FOLD is always index 0 (when legal)
/// - CALL is always index 1
/// - RAISE is always index 2 (when legal)
#[inline]
pub fn action_to_index(action: ConcreteAction) -> usize {
    match action {
        a if a == FOLD_ACTION => 0,
        a if a == CALL_ACTION => 1,  
        a if a == RAISE_ACTION => 2,
        _ => panic!("Invalid Leduc action: {:?}", action),
    }
}

/// Get action from stable index
#[inline]
pub fn index_to_action(index: usize) -> ConcreteAction {
    match index {
        0 => FOLD_ACTION,
        1 => CALL_ACTION,
        2 => RAISE_ACTION,
        _ => panic!("Invalid action index: {}", index),
    }
}

/// Convert legal actions to a bitmap for ES-CFR
/// Returns a bool array where true means the action at that index is legal
pub fn legal_actions_bitmap(legal_actions: &[ConcreteAction]) -> [bool; MAX_LEDUC_ACTIONS] {
    let mut bitmap = [false; MAX_LEDUC_ACTIONS];
    for &action in legal_actions {
        bitmap[action_to_index(action)] = true;
    }
    bitmap
}

/// Get the number of legal actions from a bitmap
pub fn count_legal_actions(bitmap: &[bool; MAX_LEDUC_ACTIONS]) -> usize {
    bitmap.iter().filter(|&&b| b).count()
}
```

crates/games/src/leduc/state/betting.rs:
```
//! Betting logic for Leduc poker

use crate::leduc::{
    action::{CALL_ACTION, FOLD_ACTION, RAISE_ACTION},
    constants::*,
    state::core::LeducState,
};
use engine::{
    error::{GameError, GameResult},
    types::{ConcreteAction, PlayerId},
};

/// Check if the current betting round is complete
pub fn is_round_complete(state: &LeducState) -> bool {
    // Round is complete when both players have acted and stakes are matched
    let num_active = (0..NUM_PLAYERS).filter(|&p| !state.folded[p]).count();
    
    if num_active <= 1 {
        return true; // Someone folded
    }
    
    // Check if both players have matched the stakes
    for p in 0..NUM_PLAYERS {
        if !state.folded[p] && state.round_contribution[p] < state.stakes {
            return false; // This player hasn't matched stakes yet
        }
    }
    
    // Both players have acted at least once (except pre-deal)
    state.betting_sequence.len() >= 2
}

/// Get legal betting actions for the current player
pub fn legal_actions(state: &LeducState) -> Vec<ConcreteAction> {
    let player = state.current_player as usize;
    
    // For ES-CFR to work correctly, we need stable action ordering.
    // We'll use a different approach: always include all actions in a fixed order,
    // but only include those that are actually legal.
    // The key is that actions must always appear at the same indices.
    
    // To solve this, we'll use a fixed-size array approach where:
    // - Index 0: FOLD (when legal)
    // - Index 1: CALL (always legal)  
    // - Index 2: RAISE (when legal)
    
    let to_call = state.stakes.saturating_sub(state.round_contribution[player]);
    let can_fold = to_call > 0 && state.stacks[player] > 0;
    let can_raise = state.num_raises < state.settings.max_raises[state.round] && 
                    state.stacks[player] >= to_call + state.settings.bet_sizes[state.round];
    
    // Build action list maintaining stable indices
    let mut actions = Vec::with_capacity(3);
    
    // Always check actions in the same order to maintain index stability
    if can_fold {
        actions.push(FOLD_ACTION);
    }
    actions.push(CALL_ACTION); // Always legal
    if can_raise {
        actions.push(RAISE_ACTION);
    }
    
    actions
}

/// Apply a betting action
pub fn apply_action(state: &mut LeducState, player: PlayerId, action: ConcreteAction) -> GameResult<()> {
    let player_idx = player as usize;
    
    // Store undo information before making changes
    let prev_round = state.round;
    let prev_stakes = state.stakes;
    let prev_pot = state.pot;
    let prev_num_raises = state.num_raises;
    let prev_round_contribution = state.round_contribution;
    let prev_player_contribution = state.player_contribution; // *** FIXED: Store this too ***
    let prev_folded = state.folded[player_idx];
    let prev_stacks = state.stacks;
    let prev_cards_dealt_this_round = state.cards_dealt_this_round;
    let prev_betting_sequence = state.betting_sequence.clone();
    
    let result = match action {
        a if a == FOLD_ACTION => {
            // Check if player is actually facing a bet
            let to_call = state.stakes.saturating_sub(state.round_contribution[player_idx]);
            if to_call == 0 {
                return Err(GameError::InvalidAction { action });
            }
            
            state.folded[player_idx] = true;
            Ok(())
        }
        a if a == CALL_ACTION => {
            // Match the current stakes
            let to_call = state.stakes.saturating_sub(state.round_contribution[player_idx]);
            let actual_call = to_call.min(state.stacks[player_idx]);
            
            state.stacks[player_idx] -= actual_call;
            state.round_contribution[player_idx] += actual_call;
            state.player_contribution[player_idx] += actual_call;
            state.pot += actual_call;
            
            Ok(())
        }
        a if a == RAISE_ACTION => {
            let raise_amount = state.settings.bet_sizes[state.round];
            
            // First call, then raise
            let to_call = state.stakes.saturating_sub(state.round_contribution[player_idx]);
            let total_amount = to_call + raise_amount;
            
            if state.stacks[player_idx] < total_amount {
                return Err(GameError::InvalidState("Insufficient funds for raise".to_string()));
            }
            
            state.stacks[player_idx] -= total_amount;
            state.round_contribution[player_idx] += total_amount;
            state.player_contribution[player_idx] += total_amount;
            state.pot += total_amount;
            
            // Update stakes
            if state.stakes == 0 {
                // Opening bet - DOES count toward raise cap in canonical Leduc
                state.stakes = raise_amount;
                state.num_raises += 1;  // Fixed: Opening bet counts as first "raise"
            } else {
                // Genuine raise
                state.stakes += raise_amount;
                state.num_raises += 1;
            }
            
            Ok(())
        }
        _ => Err(GameError::InvalidAction { action }),
    };
    
    // Store undo info if action was successful
    if result.is_ok() {
        // Check if this action completes the round BEFORE we modify state
        let will_complete_round = is_round_complete(state);
        
        state.undo_history.push((
            player,
            action,
            Some(crate::leduc::undo::UndoInfo::PlayerAction {
                prev_round,
                prev_stakes,
                prev_pot,
                prev_num_raises,
                prev_round_contribution,
                prev_player_contribution, // *** FIXED: Include this field ***
                prev_folded,
                prev_stacks,
                prev_cards_dealt_this_round,
                prev_betting_sequence,
            })
        ));
        state.history_len += 1;
        
        // If this action completes the round, handle the transition here atomically
        if will_complete_round && state.round == 0 {
            // The round transition will be handled in core.rs, but we've already
            // saved the pre-transition state in the undo record above
        }
    }
    
    result
}
```

crates/games/src/leduc/state/core.rs:
```
//! Core LeducState implementation

use crate::leduc::{
    action::{CALL_ACTION, FOLD_ACTION, RAISE_ACTION},
    constants::*,
    game::LeducGame,
    settings::LeducSettings,
    state::{betting, dealing, infoset, showdown},
};
use crate::Chips;
use engine::{
    error::{GameError, GameResult},
    game::Game,
    policy::PackedPolicy,
    state::State,
    types::{
        ConcreteAction, ConcreteActionsAndProbs, InfosetHashKey, PlayerId, Prob, Utility,
        CHANCE_PLAYER_ID, TERMINAL_PLAYER_ID,
    },
};
use fastcards::{
    card::Card,
    fast_deck::ORDERED_LEDUC_FAST_DECK,
    FastDeckTrait,
};
use cfr_rng::CfrRngPool;
use smallvec::SmallVec;
use std::fmt;

/// Leduc poker state
#[derive(Debug, Clone)]
pub struct LeducState {
    // Game settings (owned copy)
    pub settings: LeducSettings,
    
    pub current_player: PlayerId,
    pub round: usize, // 0 = first betting round, 1 = second betting round
    
    // Cards - simple arrays since we have at most 1 hole card and 1 community card
    pub deck: Box<dyn FastDeckTrait>,
    pub hole_cards: [Option<Card>; NUM_PLAYERS], // One hole card per player
    pub community_card: Option<Card>,
    pub cards_dealt_this_round: usize,
    
    // Betting state
    pub pot: Chips,
    pub stakes: Chips, // Current bet level to call
    pub num_raises: usize, // Number of raises this round
    pub player_contribution: [Chips; NUM_PLAYERS], // Total contributed by each player
    pub round_contribution: [Chips; NUM_PLAYERS], // Contributed this round
    pub folded: [bool; NUM_PLAYERS],
    pub stacks: [Chips; NUM_PLAYERS],
    
    // Action tracking
    pub betting_sequence: SmallVec<[ConcreteAction; MAX_ACTIONS_PER_ROUND * NUM_ROUNDS]>,
    pub action_history: SmallVec<[(PlayerId, ConcreteAction); 32]>,
    
    // Undo tracking
    pub history_len: usize,
    pub undo_history: Vec<(PlayerId, ConcreteAction, Option<crate::leduc::undo::UndoInfo>)>,
    
    // Terminal state
    pub winner: Option<PlayerId>,
}

impl LeducState {
    /// Create a new Leduc game state
    pub fn new(game: &LeducGame, dealer_btn: PlayerId, rng_pool: &mut CfrRngPool) -> Self {
        let settings = game.settings();
        assert_eq!(settings.num_players, NUM_PLAYERS);
        assert!(dealer_btn < NUM_PLAYERS);
        
        // Create and shuffle a Leduc deck
        let mut deck = ORDERED_LEDUC_FAST_DECK.clone();
        deck.shuffle_with_cfr_rng(rng_pool);
        
        // Box the deck
        let boxed_deck: Box<dyn FastDeckTrait> = Box::new(deck);
        
        // Initialize stacks and ante
        let mut stacks = [settings.starting_stack; NUM_PLAYERS];
        let mut player_contribution = [0; NUM_PLAYERS];
        let mut pot = 0;
        
        // Post antes
        for i in 0..NUM_PLAYERS {
            let ante = settings.ante.min(stacks[i]);
            stacks[i] -= ante;
            player_contribution[i] += ante;
            pot += ante;
        }
        
        Self {
            settings: settings.clone(),
            current_player: CHANCE_PLAYER_ID, // Start with dealing
            round: 0,
            
            deck: boxed_deck,
            hole_cards: [None; NUM_PLAYERS],
            community_card: None,
            cards_dealt_this_round: 0,
            
            pot,
            stakes: 0,
            num_raises: 0,
            player_contribution,
            round_contribution: [0; NUM_PLAYERS],
            folded: [false; NUM_PLAYERS],
            stacks,
            
            betting_sequence: SmallVec::new(),
            action_history: SmallVec::new(),
            
            history_len: 0,
            undo_history: Vec::with_capacity(32),
            
            winner: None,
        }
    }
    
    /// Get the player who acts first (non-dealer in canonical Leduc)
    #[inline]
    pub fn first_to_act(&self) -> PlayerId {
        first_to_act(self.round, NUM_PLAYERS)
    }
    
    /// Get the next player to act in a circular manner
    pub fn next_player(&self) -> PlayerId {
        let mut next = (self.current_player + 1) % NUM_PLAYERS;
        
        // Skip folded players
        while self.folded[next] && next != self.current_player {
            next = (next + 1) % NUM_PLAYERS;
        }
        
        // If everyone folded except current player, game should be terminal
        if next == self.current_player && self.folded[next] {
            return TERMINAL_PLAYER_ID;
        }
        
        next
    }
    
    /// Check if the current betting round is complete
    fn is_betting_round_complete(&self) -> bool {
        betting::is_round_complete(self)
    }
    
    /// Calculate returns for each player
    fn calculate_returns(&self) -> [Utility; NUM_PLAYERS] {
        showdown::calculate_returns(self)
    }
}

// Implement the State trait for LeducState
impl State for LeducState {
    type Game = LeducGame;
    
    fn current_player(&self) -> PlayerId {
        self.current_player
    }
    
    fn num_players(&self) -> usize {
        NUM_PLAYERS
    }
    
    fn apply_action(&mut self, action: ConcreteAction) -> GameResult<()> {
        // Handle chance actions (dealing cards)
        if self.current_player == CHANCE_PLAYER_ID {
            return dealing::apply_chance_action(self, action);
        }
        
        // Handle player actions
        let player = self.current_player;
        if player >= NUM_PLAYERS {
            return Err(GameError::InvalidPlayer { player });
        }
        
        // Record action in history
        self.action_history.push((player, action));
        
        // Apply the betting action (this will save undo info BEFORE we modify betting_sequence)
        betting::apply_action(self, player, action)?;
        
        // Now add to betting_sequence AFTER undo info has been saved
        self.betting_sequence.push(action);
        
        // Check if we need to advance the game state
        if self.is_betting_round_complete() {
            // Check for showdown
            let num_active = (0..NUM_PLAYERS).filter(|&p| !self.folded[p]).count();
            
            if num_active == 1 {
                // One player left, they win
                let winner = (0..NUM_PLAYERS).find(|&p| !self.folded[p]).unwrap();
                self.winner = Some(winner);
                self.current_player = TERMINAL_PLAYER_ID;
            } else if self.round == 1 {
                // End of second round, go to showdown
                let winner = showdown::determine_winner(self);
                self.winner = Some(winner);
                self.current_player = TERMINAL_PLAYER_ID;
            } else {
                // Move to next round
                log::trace!("[LEDUC] Round complete, advancing from round {} to {}", self.round, self.round + 1);
                log::trace!("[LEDUC] Before reset: stakes={}, num_raises={}", self.stakes, self.num_raises);
                self.round += 1;
                self.num_raises = 0;
                self.stakes = 0;
                self.round_contribution = [0; NUM_PLAYERS];
                self.cards_dealt_this_round = 0;
                self.betting_sequence.clear(); // Reset betting sequence for new round
                self.current_player = CHANCE_PLAYER_ID; // Deal community card
                log::trace!("[LEDUC] After reset: stakes={}, num_raises={}, current_player=CHANCE", self.stakes, self.num_raises);
            }
        } else {
            // Continue betting in current round
            self.current_player = self.next_player();
        }
        
        Ok(())
    }
    
    fn legal_actions(&self) -> Vec<ConcreteAction> {
        if self.is_terminal() {
            return vec![];
        }
        
        if self.current_player == CHANCE_PLAYER_ID {
            return dealing::legal_chance_actions(self);
        }
        
        betting::legal_actions(self)
    }
    
    fn action_to_string(&self, player: PlayerId, action: ConcreteAction) -> String {
        if player == CHANCE_PLAYER_ID {
            return dealing::chance_action_to_string(self, action);
        }
        
        match action {
            FOLD_ACTION => "Fold".to_string(),
            CALL_ACTION => {
                let to_call = self.stakes.saturating_sub(self.round_contribution[player as usize]);
                if to_call > 0 {
                    format!("Call {}", to_call)
                } else {
                    "Check".to_string()
                }
            }
            RAISE_ACTION => {
                let raise_amount = self.settings.bet_sizes[self.round];
                if self.stakes == 0 {
                    format!("Bet {}", raise_amount)
                } else {
                    format!("Raise to {}", self.stakes + raise_amount)
                }
            }
            _ => format!("Unknown({})", action.0),
        }
    }
    
    fn is_terminal(&self) -> bool {
        self.current_player == TERMINAL_PLAYER_ID
    }
    
    fn returns(&self) -> Vec<Utility> {
        if !self.is_terminal() {
            return vec![0.0; NUM_PLAYERS];
        }
        
        let returns_array = self.calculate_returns();
        returns_array.to_vec()
    }
    
    fn rewards(&self) -> Vec<Utility> {
        // Leduc only has rewards at terminal states
        self.returns()
    }
    
    fn is_chance_node(&self) -> bool {
        self.current_player == CHANCE_PLAYER_ID
    }
    
    fn chance_outcomes(&self) -> ConcreteActionsAndProbs {
        if !self.is_chance_node() {
            return Vec::new();
        }
        
        dealing::chance_outcomes(self)
    }
    
    fn information_state_key(&self, player: PlayerId) -> InfosetHashKey {
        infoset::information_state_key(self, player)
    }
    
    fn history(&self) -> &[(PlayerId, ConcreteAction)] {
        &self.action_history
    }
    
    fn to_string(&self) -> String {
        let mut s = format!("Leduc State:\n");
        s.push_str(&format!("  Round: {}\n", self.round));
        s.push_str(&format!("  Current: {}\n", 
            match self.current_player {
                CHANCE_PLAYER_ID => "Chance".to_string(),
                TERMINAL_PLAYER_ID => "Terminal".to_string(),
                p => format!("Player {}", p),
            }
        ));
        s.push_str(&format!("  Pot: {}\n", self.pot));
        s.push_str(&format!("  Stakes: {}\n", self.stakes));
        
        // Show hole cards
        for p in 0..NUM_PLAYERS {
            if let Some(card) = self.hole_cards[p] {
                s.push_str(&format!("  P{} card: {}\n", p, card));
            }
        }
        
        // Show community card
        if let Some(card) = self.community_card {
            s.push_str(&format!("  Community: {}\n", card));
        }
        
        s
    }
    
    fn debug_string_with_actions(&self, _packed_policy: &PackedPolicy) -> String {
        let mut s = State::to_string(self);
        
        if !self.is_terminal() && self.current_player != CHANCE_PLAYER_ID {
            s.push_str("\nLegal actions:\n");
            let actions = self.legal_actions();
            
            // For now, just show actions without probabilities
            // TODO: Implement proper policy lookup when integrated with solvers
            for &action in &actions {
                let action_str = self.action_to_string(self.current_player, action);
                s.push_str(&format!("  {}\n", action_str));
            }
        }
        
        s
    }
    
    fn undo_last_action(&mut self) -> GameResult<()> {
        if self.history_len == 0 {
            return Err(GameError::LogicError("Cannot undo from initial state".into()));
        }
        
        // Decrement history length and get the action to undo
        self.history_len -= 1;
        let (player, _action, undo_info) = self.undo_history[self.history_len].clone();
        
        // Clear winner flag as state is no longer terminal
        self.winner = None;
        
        // Pop from action_history 
        self.action_history.pop();
        
        // Also pop from undo_history
        self.undo_history.pop();
        
        // Apply undo based on type
        match undo_info {
            Some(crate::leduc::undo::UndoInfo::Deal { 
                card, 
                recipient, 
                prev_betting_sequence, 
                prev_stakes,
                prev_num_raises,
                prev_round_contribution,
            }) => {
                // Undo a deal action
                
                // Add card back to deck (like HULH does)
                if !self.deck.add_card_to_deck(card) {
                    log::error!("Failed to add card {:?} back to deck during undo. Deck state: {:?}", 
                        card, self.deck.available_cards_vec());
                    return Err(GameError::LogicError("Failed to restore card to deck".into()));
                }
                
                if let Some(player_idx) = recipient {
                    // Undo hole card deal
                    self.hole_cards[player_idx] = None;
                    self.cards_dealt_this_round -= 1;
                    
                    // Restore player to act (if we're back to dealing phase)
                    if self.cards_dealt_this_round > 0 {
                        self.current_player = CHANCE_PLAYER_ID;
                    } else {
                        // First deal of the round, go back to previous round's last player
                        if self.round == 0 {
                            self.current_player = CHANCE_PLAYER_ID;
                        } else {
                            // Go back to end of previous betting round
                            self.round = 0;
                            self.current_player = second_to_act(NUM_PLAYERS);
                            self.cards_dealt_this_round = NUM_PLAYERS;
                            self.stakes = 0;
                            self.num_raises = 0;
                            self.round_contribution = [0; NUM_PLAYERS];
                        }
                    }
                } else {
                    // Undo community card deal
                    self.community_card = None;
                    self.cards_dealt_this_round = 0;
                    
                    // Stay in round 1, but go back to dealing phase
                    self.current_player = CHANCE_PLAYER_ID;
                    
                    // Restore betting state from before the community card deal
                    if let Some(stakes) = prev_stakes {
                        self.stakes = stakes;
                    }
                    if let Some(num_raises) = prev_num_raises {
                        self.num_raises = num_raises;
                    }
                    if let Some(round_contribution) = prev_round_contribution {
                        self.round_contribution = round_contribution;
                    }
                    if let Some(betting_sequence) = prev_betting_sequence {
                        self.betting_sequence = betting_sequence;
                    }
                }
            }
            Some(crate::leduc::undo::UndoInfo::PlayerAction {
                prev_round,
                prev_stakes,
                prev_pot,
                prev_num_raises,
                prev_round_contribution,
                prev_player_contribution, // *** FIXED: Added this field ***
                prev_folded,
                prev_stacks,
                prev_cards_dealt_this_round,
                prev_betting_sequence,
            }) => {
                // Restore all state from before the action
                self.round = prev_round;
                self.stakes = prev_stakes;
                self.pot = prev_pot;
                self.num_raises = prev_num_raises;
                self.round_contribution = prev_round_contribution;
                self.player_contribution = prev_player_contribution; // *** FIXED: Restore this too ***
                self.folded[player as usize] = prev_folded;
                self.stacks = prev_stacks;
                self.cards_dealt_this_round = prev_cards_dealt_this_round;
                self.betting_sequence = prev_betting_sequence;
                
                // Restore current player
                self.current_player = player;
            }
            None => {
                return Err(GameError::LogicError("Missing undo information".into()));
            }
        }
        
        Ok(())
    }
    
    fn sample_chance_action(&self, _rng_pool: &CfrRngPool) -> Option<(ConcreteAction, Prob)> {
        if !self.is_chance_node() {
            return None;
        }
        
        let num_available = self.deck.len();
        if num_available == 0 {
            return None;
        }
        
        // Peek the next card from the pre-shuffled deck (like HULH)
        let sampled_card = self.deck.peek_next_card()
            .expect("Deck should have a card if num_available > 0");
        let sampled_action = ConcreteAction(sampled_card.standard_deck_index() as u64);
        let prob = 1.0 / num_available as Prob;
        Some((sampled_action, prob))
    }
}

// Manual PartialEq implementation for LeducState
impl PartialEq for LeducState {
    fn eq(&self, other: &Self) -> bool {
        self.settings == other.settings &&
        self.stacks == other.stacks &&
        self.pot == other.pot &&
        self.stakes == other.stakes &&
        self.num_raises == other.num_raises &&
        self.round == other.round &&
        self.current_player == other.current_player &&
        self.cards_dealt_this_round == other.cards_dealt_this_round &&
        &self.deck == &other.deck &&
        self.hole_cards == other.hole_cards &&
        self.community_card == other.community_card &&
        self.folded == other.folded &&
        self.round_contribution == other.round_contribution &&
        self.player_contribution == other.player_contribution &&
        self.betting_sequence == other.betting_sequence &&
        self.action_history == other.action_history &&
        self.undo_history == other.undo_history &&
        self.winner == other.winner &&
        self.history_len == other.history_len
    }
}

impl Eq for LeducState {}

// Implement Display for LeducState
impl fmt::Display for LeducState {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", State::to_string(self))
    }
}
```

crates/games/src/leduc/state/dealing.rs:
```
//! Card dealing logic for Leduc poker

use crate::leduc::{
    constants::*,
    state::core::LeducState,
};
use engine::{
    error::{GameError, GameResult},
    types::{ConcreteAction, ConcreteActionsAndProbs, PlayerId, Prob, CHANCE_PLAYER_ID},
};
use fastcards::card::Card;

/// Get legal chance actions (which cards can be dealt)
pub fn legal_chance_actions(state: &LeducState) -> Vec<ConcreteAction> {
    if state.round == 0 && state.cards_dealt_this_round < NUM_PLAYERS {
        // Dealing hole cards - return available cards from deck
        state.deck.available_cards_vec()
            .iter()
            .map(|card| ConcreteAction(card.standard_deck_index() as u64))
            .collect()
    } else if state.round == 1 && state.cards_dealt_this_round == 0 {
        // Dealing community card - return available cards from deck
        state.deck.available_cards_vec()
            .iter()
            .map(|card| ConcreteAction(card.standard_deck_index() as u64))
            .collect()
    } else {
        vec![]
    }
}

/// Apply a chance action (deal a card)
pub fn apply_chance_action(state: &mut LeducState, action: ConcreteAction) -> GameResult<()> {
    // Convert action to card using standard deck index
    let card = match Card::from_standard_deck_index(action.0 as usize) {
        Some(c) => c,
        None => return Err(GameError::InvalidAction { action }),
    };
    
    // Remove card from deck (like HULH does)
    if !state.deck.remove_card_from_deck(card) {
        log::error!("Failed to remove card {:?} from deck. Deck state: {:?}", 
            card, state.deck.available_cards_vec());
        return Err(GameError::LogicError(
            "Card not found in deck for removal".into()
        ));
    }
    
    // Record in history
    state.action_history.push((CHANCE_PLAYER_ID, action));
    
    if state.round == 0 && state.cards_dealt_this_round < NUM_PLAYERS {
        // Deal hole card - temporarily always deal in fixed order P0, P1 to match action order hack
        let player_to_deal = state.cards_dealt_this_round % NUM_PLAYERS;
        state.hole_cards[player_to_deal] = Some(card);
        
        state.cards_dealt_this_round += 1;
        
        // Check if we need to deal more hole cards
        if state.cards_dealt_this_round < NUM_PLAYERS {
            // Continue dealing
            state.current_player = CHANCE_PLAYER_ID;
        } else {
            // All hole cards dealt, start betting
            let first_player = state.first_to_act();
            state.current_player = first_player;
        }
    } else if state.round == 1 && state.cards_dealt_this_round == 0 {
        // Deal community card
        // CRITICAL FIX: Don't save betting state here - it was already reset
        // The PlayerAction that caused round completion saved the real end-of-round-0 state
        
        state.community_card = Some(card);
        state.cards_dealt_this_round = 1;
        
        // Start second round betting
        let first_player = state.first_to_act();
        state.current_player = first_player;
        log::trace!("[DEALING] Community card dealt, first to act: Player {}", first_player);
    } else {
        return Err(GameError::InvalidState("Invalid dealing state".to_string()));
    }
    
    // Store undo info after successful dealing
    let undo_info = if state.round == 0 {
        // Just dealt to a player - using fixed order to match action order hack
        crate::leduc::undo::UndoInfo::Deal {
            card,
            recipient: Some(((state.cards_dealt_this_round - 1) % NUM_PLAYERS) as PlayerId),
            prev_betting_sequence: None,
            prev_stakes: None,
            prev_num_raises: None,
            prev_round_contribution: None,
        }
    } else {
        // Dealt community card - DON'T save betting state (it's already reset)
        crate::leduc::undo::UndoInfo::Deal {
            card,
            recipient: None,
            prev_betting_sequence: None,
            prev_stakes: None,
            prev_num_raises: None,
            prev_round_contribution: None,
        }
    };
    
    state.undo_history.push((
        CHANCE_PLAYER_ID,
        action,
        Some(undo_info)
    ));
    state.history_len += 1;
    
    Ok(())
}

/// Get chance outcomes with probabilities
pub fn chance_outcomes(state: &LeducState) -> ConcreteActionsAndProbs {
    // Standard random dealing - use deck's available cards
    let num_available = state.deck.len();
    if num_available == 0 {
        return ConcreteActionsAndProbs::new();
    }
    
    let prob = 1.0 / num_available as Prob;
    state.deck.available_cards_vec()
        .iter()
        .map(|card| (ConcreteAction(card.standard_deck_index() as u64), prob))
        .collect()
}

/// Convert a chance action to string
pub fn chance_action_to_string(state: &LeducState, action: ConcreteAction) -> String {
    let card = match Card::from_standard_deck_index(action.0 as usize) {
        Some(c) => c,
        None => return format!("Invalid card index {}", action.0),
    };
    
    if state.round == 0 {
        format!("Deal {} to P{}", card, state.cards_dealt_this_round % NUM_PLAYERS)
    } else {
        format!("Deal community {}", card)
    }
}
```

crates/games/src/leduc/state/infoset.rs:
```
//! Information set key generation for Leduc poker

use crate::leduc::{
    constants::*,
    state::core::LeducState,
};
use engine::{
    types::{InfosetHashKey, PlayerId},
    position::{SeatNumber, ButtonSeat},
};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

/// Generate information state key for a player
pub fn information_state_key(state: &LeducState, player: PlayerId) -> InfosetHashKey {
    if player >= NUM_PLAYERS {
        return InfosetHashKey(u64::MAX);
    }
    
    let mut hasher = DefaultHasher::new();
    
    // Hash the player's hole card RANK ONLY (suits don't matter in Leduc)
    if let Some(card) = state.hole_cards[player] {
        card.rank_index().hash(&mut hasher);
        // DON'T hash suit - suits are irrelevant in Leduc
    } else {
        // No hole card dealt yet
        return InfosetHashKey(u64::MAX);
    }
    
    // Hash the community card RANK ONLY if available
    if let Some(card) = state.community_card {
        card.rank_index().hash(&mut hasher);
        // DON'T hash suit - suits are irrelevant in Leduc
    }
    
    // Hash the betting sequence without player identities
    // Just the sequence of actions matters, not who took them
    for &(player_id, action) in &state.action_history {
        // Only hash betting actions, not chance actions
        if player_id != engine::types::CHANCE_PLAYER_ID {
            // Just hash the action, not the player
            // This makes the infoset position-independent
            action.0.hash(&mut hasher);
        }
    }
    
    // Hash the round number to distinguish pre/post community card states
    state.round.hash(&mut hasher);
    
    // DON'T hash button position or player seat - these create unnecessary duplicates
    // In perfect information abstraction, only the cards and action sequence matter

    InfosetHashKey(hasher.finish())
}
```

crates/games/src/leduc/state/mod.rs:
```
//! Submodules defining the logic for HulhState.

pub(crate) mod betting;
pub mod core;
pub mod dealing; // Made public for bucketed_get_chance_outcomes
pub(crate) mod infoset;
pub mod showdown; // Made public for test access to counter
pub mod action_mapping; // Action index mapping for ES-CFR

```

crates/games/src/leduc/state/showdown.rs:
```
//! Showdown logic for Leduc poker

use crate::leduc::{
    constants::*,
    state::core::LeducState,
};
use engine::types::{PlayerId, Utility};
use fastcards::eval::evaluate_leduc_hand;
use smallvec::SmallVec;

/// Determine all winners at showdown (handles ties)
pub fn determine_winners(state: &LeducState) -> SmallVec<[PlayerId; NUM_PLAYERS]> {
    let community = state.community_card.expect("Community card should be dealt at showdown");
    
    let mut winners = SmallVec::new();
    let mut best_rank = u16::MAX; // Lower rank is better in fastcards
    
    for p in 0..NUM_PLAYERS {
        if state.folded[p] {
            continue;
        }
        
        let hole = state.hole_cards[p].expect("Hole card should be dealt");
        let rank = evaluate_leduc_hand(hole, community);
        
        // In fastcards, lower rank value is better (1 = best, 6 = worst)
        if rank < best_rank {
            best_rank = rank;
            winners.clear();
            winners.push(p);
        } else if rank == best_rank {
            winners.push(p);
        }
    }
    
    winners
}

/// Determine the winner at showdown (for backward compatibility)
pub fn determine_winner(state: &LeducState) -> PlayerId {
    let winners = determine_winners(state);
    winners[0] // Return the first winner
}

/// Calculate returns for each player
pub fn calculate_returns(state: &LeducState) -> [Utility; NUM_PLAYERS] {
    let mut returns = [0.0; NUM_PLAYERS];
    
    // Everyone loses their contribution initially
    for p in 0..NUM_PLAYERS {
        returns[p] = -(state.player_contribution[p] as Utility);
    }
    
    if state.winner.is_some() {
        // Count active players (not folded)
        let active_players = (0..NUM_PLAYERS).filter(|&p| !state.folded[p]).count();
        
        // Get all winners (handles ties)
        let winners = if active_players == 1 {
            // Win by fold - only one player remains
            let mut w = SmallVec::<[PlayerId; NUM_PLAYERS]>::new();
            w.push(state.winner.unwrap());
            w
        } else {
            // Multiple players remain - determine winners at showdown
            determine_winners(state)
        };
        
        let num_winners = winners.len();
        if num_winners > 0 {
            // Split pot evenly among winners using floating-point division (like OpenSpiel)
            let share = state.pot as Utility / num_winners as Utility;
            
            // Distribute equal share to all winners
            for &winner in &winners {
                returns[winner] += share;
            }
        }
    }
    
    returns
}
```

crates/games/src/leduc/undo.rs:
```
//! Undo functionality for Leduc poker
//!
//! Provides the ability to undo actions during game tree traversal,
//! which is required by the BR (Best Response) crate for efficient
//! tree exploration without cloning states.

use crate::leduc::constants::{NUM_PLAYERS, MAX_ACTIONS_PER_ROUND, NUM_ROUNDS};
use crate::Chips;
use engine::types::{ConcreteAction, PlayerId};
use fastcards::card::Card;
use smallvec::SmallVec;

/// Information needed to undo an action in Leduc
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UndoInfo {
    /// Undo information for deal (chance) actions
    Deal {
        /// The card that was dealt
        card: Card,
        /// Which player received the card (None for community card)
        recipient: Option<PlayerId>,
        /// Previous betting sequence (in case we're undoing community card deal)
        prev_betting_sequence: Option<SmallVec<[ConcreteAction; MAX_ACTIONS_PER_ROUND * NUM_ROUNDS]>>,
        /// Previous betting state (for community card deals that reset the betting)
        prev_stakes: Option<Chips>,
        prev_num_raises: Option<usize>,
        prev_round_contribution: Option<[Chips; NUM_PLAYERS]>,
    },
    
    /// Undo information for player actions (fold, call, raise)
    PlayerAction {
        /// Previous game state values
        prev_round: usize,
        prev_stakes: Chips,
        prev_pot: Chips,
        prev_num_raises: usize,
        prev_round_contribution: [Chips; NUM_PLAYERS],
        prev_player_contribution: [Chips; NUM_PLAYERS], // *** FIXED: Added this field ***
        prev_folded: bool, // Only for the acting player
        prev_stacks: [Chips; NUM_PLAYERS],
        prev_cards_dealt_this_round: usize,
        prev_betting_sequence: SmallVec<[ConcreteAction; MAX_ACTIONS_PER_ROUND * NUM_ROUNDS]>,
    },
}
```

crates/games/src/leduc/utils.rs:
```
//! Utility functions for Leduc poker

use crate::leduc::settings::LeducSettings;
use crate::Chips;

/// Calculates the maximum possible commitment a single player can make in a Leduc hand.
pub fn calculate_max_commitment(settings: &LeducSettings) -> Chips {
    // Start with ante
    let mut max_commitment = settings.ante;
    
    // For each round, calculate maximum possible betting
    for round_idx in 0..settings.num_rounds {
        let bet_size = settings.bet_sizes[round_idx];
        let max_raises = settings.max_raises[round_idx];
        
        // In each round: initial bet + (raise * max_raises)
        // Example round 0: bet 2 + raise to 4 + raise to 6 = 6 total
        // Example round 1: bet 4 + raise to 8 + raise to 12 = 12 total
        let round_contribution = bet_size * (max_raises + 1) as Chips;
        max_commitment += round_contribution;
    }
    
    max_commitment
}

/// Check if a player has enough chips to make a bet/raise
pub fn can_afford_action(stack: Chips, amount_to_call: Chips, raise_amount: Chips) -> bool {
    stack >= amount_to_call + raise_amount
}

/// Calculate pot odds for calling
pub fn pot_odds(pot: Chips, amount_to_call: Chips) -> f64 {
    if amount_to_call == 0 {
        return f64::INFINITY; // Free to call
    }
    pot as f64 / amount_to_call as f64
}
```

crates/algorithms/src/chance_sampling_cfr.rs:
```
/*! Chance-Sampling MCCFR solver.

This follows the structure of `vanilla_cfr.rs` but samples **one** chance
outcome at every chance node (Lanctot 2009 “chance sampling CFR”).
Opponent actions are *not* sampled (unlike external sampling); they are all
enumerated exactly as in the vanilla solver.

The implementation purposefully re-uses helper modules (`es_util`, `regretmap`,
`inc_metric!` macro, etc.) so that only minimal new code is introduced.
*/

#![allow(missing_docs)]
#![deny(unsafe_code)]

use std::sync::Arc;

use cfr_rng::CfrRngPool;
use engine::{
	abstraction::InformationAbstraction,
	game::Game,
	policy::{PackedPolicy, TabularPolicy},
	solver::{PlayerAwareSolver, Solver},
	state::State,
	types::{PlayerId, Prob, Utility, CHANCE_PLAYER_ID, MAX_GRID},
};
use crate::util::index_to_concrete_action;
// Removed unused log imports: error, trace
use regretmap::InfoStatesMap;

use crate::inc_metric; // <-- REMOVE SolverConfig from here
use engine::solver_config::SolverConfig; // <-- ADD THIS LINE

/// Chance-Sampling MCCFR (CS-CFR) – single-threaded, uniform iteration weighting.
pub struct ChanceSamplingCfr<G: Game> {
	game: Arc<G>,
	abstraction: Arc<dyn InformationAbstraction<G>>,
	info_states: Arc<InfoStatesMap>,
	rng_pool: CfrRngPool,   // Keep rng_pool field
	_config: SolverConfig,  // <-- Prefix with underscore
}

// Removed new() constructor - use with_abstraction() to explicitly pass information abstraction

impl<G> ChanceSamplingCfr<G>
where
	G: Game,
	G::State: State<Game = G> + 'static,
{
	#[allow(clippy::too_many_arguments)]
	pub fn with_abstraction(
		game: Arc<G>,
		abstraction: Arc<dyn InformationAbstraction<G>>,
		info_states: Arc<InfoStatesMap>,
		rng_pool: CfrRngPool,  // <-- ADD rng_pool parameter
		_config: SolverConfig, // <-- Prefix with underscore
	) -> Self {
		// rng_pool is now passed in

		Self {
			game,
			abstraction,
			info_states,
			rng_pool,                          // Use passed rng_pool
			_config,                           // <-- Use prefixed name
		}
	}

	/* ------------------------------------------------------------------ */

	fn run_one_traversal(&mut self, player_to_update: PlayerId) {
		inc_metric!(ITERS, 1);
		let mut state = self.game.new_initial_state(&mut self.rng_pool);
		let n = self.game.num_players();

		// reach_probs[0..n] – players,  reach_probs[n] – chance
		let mut reach_probs = vec![1.0; n + 1];

		let mut utils_buf = vec![0.0; n];
		let mut child_buf = vec![0.0; n];

		self.cs_cfr_recursive(
			&mut state,
			&mut reach_probs,
			player_to_update,
			&mut utils_buf,
			&mut child_buf,
		);
	}

	/* ---------------- RECURSIVE --------------------------------------- */

	fn cs_cfr_recursive(
		&mut self,
		state: &mut G::State,
		reach: &mut [Prob],
		update_player: PlayerId,
		utils_out: &mut [Utility],
		child_buf: &mut [Utility],
	) {
		let cur = state.current_player();
		let n = self.game.num_players();

		/* ---- terminal ------------------------------------------------ */
		if state.is_terminal() {
			utils_out.copy_from_slice(&state.returns());
			return;
		}

		/* ---- chance node – SAMPLE ONE outcome ----------------------- */
		if cur == CHANCE_PLAYER_ID {
			let (act, p) = state
				.sample_chance_action(&self.rng_pool)
				.expect("chance node with no outcomes");

			state.apply_action(act).expect("apply chance");

			let prev = reach[n];
			reach[n] *= p;

			self.cs_cfr_recursive(state, reach, update_player, utils_out, child_buf);

			reach[n] = prev;
			state.undo_last_action().expect("undo");
			return;
		}

		/* ---- player node -------------------------------------------- */
		let key = self.abstraction.key(state, cur);
		let legal_actions = state.legal_actions();
		// We don't need masks anymore - just use num_actions directly

		// load σ(I) into stack array
		let mut sigma = [0.0; MAX_GRID];
		self.info_states
			.with_row(key, legal_actions.len(), |row| {
				row.write_current_strategy_into(row.num_actions as usize, &mut sigma);
			});

		let mut node_utils = vec![0.0; n];
		// Store v(I,a) for the update-player separately so regrets are correct.
		let mut action_values = [0.0; MAX_GRID];

		for idx in 0..legal_actions.len() {
			let prob = sigma[idx];
			let concrete = index_to_concrete_action(&legal_actions, idx);

			state.apply_action(concrete).expect("apply");

			let prev = reach[cur];
			reach[cur] *= prob;

			self.cs_cfr_recursive(state, reach, update_player, child_buf, utils_out);

			reach[cur] = prev;
			state.undo_last_action().expect("undo");

			for p in 0..n {
				node_utils[p] += prob * child_buf[p];
			}

			// Save v(I,a) for regret computation *after* the loop
			action_values[idx] = child_buf[update_player];
		}

		utils_out.copy_from_slice(&node_utils[..n]);

		// ---- regret / strategy updates for traverser ------------------
		// Note: infosets_seen is incremented when row is first fetched for strategy,
		// so not incrementing again here.
		self.info_states
			.with_row(key, legal_actions.len(), |row| {
				let pi_i = reach[cur];
				let pi_opp = reach
					.iter()
					.enumerate()
					.filter(|(i, _)| *i != cur)
					.fold(1.0, |acc, (_, p)| acc * *p);

				// accumulate average strategy
				row.add_reach_denominator(pi_i);
				for (idx, &sigma_val) in sigma.iter().enumerate().take(row.num_actions as usize) {
					row.add_strategy_numerator(idx, pi_i * sigma_val);
				}

				if cur != update_player {
					return; // Return from closure
				}

				let v_i = node_utils[update_player]; // node_utils captured from outer scope
				for (idx, &action_val) in action_values.iter().enumerate().take(row.num_actions as usize) {
					let adv = action_val - v_i; // action_values captured from outer scope
					row.add_regret(idx, pi_opp * adv);
				}
			});
	}
}

/* ---------------------------------------------------------------------- */
/* ---------------- Solver trait impls ---------------------------------- */
/* ---------------------------------------------------------------------- */

impl<G> Solver<G> for ChanceSamplingCfr<G>
where
	G: Game + 'static,
	G::State: State<Game = G> + 'static,
{
	fn run_iteration(&mut self, _pool: &CfrRngPool) {
		for p in 0..self.game.num_players() {
			self.run_one_traversal(p as PlayerId);
		}
	}

	fn average_policy(&self) -> Arc<TabularPolicy<G>> {
		let mut pol = TabularPolicy::new(
			self.abstraction.clone() as Arc<dyn InformationAbstraction<G>>,
			true
		);
		for (k, row) in self.info_states.iter() {
			let packed = row.get_average_policy(Some(k)).unwrap_or(PackedPolicy {
				// fallback identical to other solvers
				num_actions: 0,
				probabilities: Default::default(),
			});
			pol.set_packed_policy(k, packed);
		}
		Arc::new(pol)
	}

	fn current_policy(&self) -> Arc<TabularPolicy<G>> {
		let mut pol = TabularPolicy::new(
			self.abstraction.clone() as Arc<dyn InformationAbstraction<G>>,
			true
		);
		for (k, row) in self.info_states.iter() {
			let packed = row.get_current_policy().unwrap_or(PackedPolicy {
				num_actions: 0,
				probabilities: Default::default(),
			});
			pol.set_packed_policy(k, packed);
		}
		Arc::new(pol)
	}

    fn num_info_states(&self) -> usize {
        self.info_states.iter().len()
    }


	fn as_any(&self) -> &dyn std::any::Any {
		self
	}
	fn as_any_mut(&mut self) -> &mut dyn std::any::Any {
		self
	}

}

impl<G> PlayerAwareSolver<G> for ChanceSamplingCfr<G>
where
	G: Game + 'static,
	G::State: State<Game = G> + 'static,
{
	fn run_iteration_for_player(&mut self, player: Option<PlayerId>, _pool: &CfrRngPool) {
		let p = player.unwrap_or(0);
		self.run_one_traversal(p);
	}
	fn mark_iteration(&mut self, _global_iteration: u64) {}
}

```

crates/algorithms/src/depth_limited_solver.rs:
```
use std::sync::Arc;
use engine::game::Game;
use engine::policy::TabularPolicy;
use engine::State;
use engine::solver_config::SolverConfig;
use regretmap::InfoStatesMap;
use cfr_rng::CfrRngPool;
use crate::external_sampling_cfr::ExternalSamplingCfr;

/// Result of a subgame solve containing both the policy and the infoset map
pub struct SubgameSolveResult<G: Game> {
    pub policy: TabularPolicy<G>,
    pub infosets: Arc<InfoStatesMap>,
}

/// Thin wrapper around ES-MCCFR for depth-limited solving
pub struct DepthLimitedSolver<G: Game> {
    es_cfr: ExternalSamplingCfr<G>,
    max_depth: usize,
    iterations: usize,
}

impl<G: Game> DepthLimitedSolver<G> 
where
    G::State: State<Game = G> + 'static,
{
    pub fn new(
        game: Arc<G>,
        blueprint: Arc<TabularPolicy<G>>,
        max_depth: usize,
        iterations: usize,
        config: SolverConfig,
    ) -> Self {
        // Create fresh InfoStatesMap for subgame solving
        // TODO: This leaks memory - known issue throughout codebase
        let config_static = Box::leak(Box::new(config.clone()));
        let subgame_infosets = Arc::new(InfoStatesMap::new(64, config_static));
        
        // Create ES-MCCFR solver with blueprint's abstraction
        let es_cfr = ExternalSamplingCfr::with_abstraction(
            game,
            blueprint.abstraction.clone(),
            subgame_infosets,
            CfrRngPool::from_entropy(),
            config,
        );
        
        Self {
            es_cfr,
            max_depth,
            iterations,
        }
    }
    
    /// Solve a subgame from the given root state
    pub fn solve_subgame(&mut self, root_state: &G::State) -> Result<SubgameSolveResult<G>, String> {
        // Set depth limit
        self.es_cfr.set_max_depth(Some(self.max_depth));
        
        // Run iterations starting from the given root state
        for _ in 0..self.iterations {
            // Run ES-MCCFR for each player from the root state
            for player in 0..self.es_cfr.game.num_players() {
                let mut state = root_state.clone();
                self.es_cfr.run_one_traversal_from_state(&mut state, player);
            }
        }
        
        // Extract policy using existing helper
        let policy = regretmap::policy_helper::infosets_to_policy(
            &self.es_cfr.info_states,
            self.es_cfr.abstraction.clone(),
            true, // use_average = true for final policy
        );
        
        Ok(SubgameSolveResult {
            policy,
            infosets: self.es_cfr.info_states.clone(),
        })
    }
}

```

crates/algorithms/src/es_factory.rs:
```
use crate::external_sampling_cfr::ExternalSamplingCfr;
// RBP imports removed - unused
use cfr_rng::CfrRngPool;
use engine::solver_config::SolverConfig;
use engine::{
	abstraction::InformationAbstraction,
	game::Game,
	state::State,
	// types::InfosetHashKey, // Unused
};
use regretmap::InfoStatesMap;
use std::sync::{
	// Removed unused AtomicOrdering import
	Arc,
};

// Removed new() constructor - use with_abstraction() to explicitly pass information abstraction

impl<G> ExternalSamplingCfr<G>
where
	G: Game + 'static,
	G::State: State<Game = G> + 'static,
{
	/// Creates a new ES-CFR solver with a specific information abstraction.
	pub fn with_abstraction(
		game: Arc<G>,
		abstraction: Arc<dyn InformationAbstraction<G>>,
		info_states: Arc<InfoStatesMap>,
		rng_pool: CfrRngPool, // Accept CfrRngPool
		config: SolverConfig,
	) -> Self {
		// Determine if VR is active based on config.vr_mode
		let use_vr = config.vr_mode != engine::solver_config::VRMode::None;

		// Note: RBP manager is now passed in as a shared Arc from the training setup
		// This ensures all solver instances share the same RBP state
		let rbp_manager = None; // Will be set via set_rbp_manager if RBP is enabled

		Self {
			game,
			abstraction,
			info_states,
			rng_pool,
			config, // Store the provided config
			iter_count: 0,
			// linear_weighting, use_vr, use_dcfr are now determined from config inside the solver logic
			// Instrumentation fields removed
			warming_up: if use_vr {
				config.warmup_iterations > 0
			} else {
				false
			},
			vr_ready: if use_vr {
				config.warmup_iterations == 0
			} else {
				false
			},
			// DCFR log factors were removed from the struct
			rbp_manager,
			max_depth: None, // No depth limit by default
			infostate_hook: None, // No hook by default
		}
	}
}

```

crates/algorithms/src/es_instrumentation.rs:
```
use crate::es_util;
use dashmap::DashMap;
use engine::types::{
	ConcreteAction, InfosetHashKey, PlayerId, Prob, Utility,
	MAX_GRID,
};
use log::{info, trace, warn};
use regretmap::InfoStatesMap;
use std::sync::atomic::{AtomicUsize, Ordering as AtomicOrdering};

// --- Instrumentation Logging Helpers ---

/// Logs the state of a row (regrets, policy nums, baseline) either at INFO or TRACE level.
#[inline]
pub fn log_row_state(
	when: &str, // "BEFORE" or "AFTER"
	row: &regretmap::Row,
	infoset_key: InfosetHashKey,
	should_log_instrumented: bool,
	iter_count: u64, // Changed to u64
	vr_ready: bool,
) {
	if should_log_instrumented {
		if when == "BEFORE" {
			// Print header only before the first log block for the key
			trace!("------------------------------------------------------------------------------------------");
			trace!(
				"[INSTRUMENT_LOG] Iter={}, Key={:?}",
				iter_count,
				infoset_key
			);
		}
		trace!("[INSTRUMENT_LOG] State {} Update:", when);
		trace!(
			"  Reach Denom Sum : {:.6}",
			row.cumulative_reach_denominator_sum.get()
		);
		for a_idx in 0..row.num_actions as usize {
			trace!(
				"  Action {:<2}: Regret={:<12.6} | PolicyNum={:<12.6}",
				a_idx,
				row.cumulative_regrets[a_idx].get(),
				row.cumulative_policy_numerator[a_idx].get()
			);
		}
		if vr_ready {
			trace!("  BaselineValue   : {:.6}", row.baseline_value.get());
		}
		if when == "AFTER" {
			// Print footer only after the last log block for the key
			trace!("------------------------------------------------------------------------------------------");
		}
	} else {
		// Original trace logging
		trace!(
			"[ROW_STATE_{}] Key={:?}, Denom={:.6}",
			when,
			infoset_key,
			row.cumulative_reach_denominator_sum.get()
		);
		for a_idx in 0..row.num_actions as usize {
			trace!(
				"  Action {}: Regret={:.6}, PolicyNum={:.6}",
				a_idx,
				row.cumulative_regrets[a_idx].get(),
				row.cumulative_policy_numerator[a_idx].get()
			);
		}
		if vr_ready {
			trace!("  BaselineValue={:.6}", row.baseline_value.get());
		}
	}
}

/// Logs the details of a regret update calculation either at INFO or TRACE level.
#[inline]
pub fn log_regret_update_details(
	infoset_key: InfosetHashKey,
	a_idx: usize,
	action_value: Utility,
	reference_value: Utility,
	regret_delta: Utility,
	opp_cf_reach: Prob,
	should_log_instrumented: bool,
	vr_ready: bool,
) {
	if should_log_instrumented {
		let vr_tag = if vr_ready { "[VR]" } else { "" };
		trace!("[INSTRUMENT_LOG] Update Details {}:", vr_tag);
		trace!("  Node Value (EV(I)/Baseline): {:.6}", reference_value);
		trace!("  Opponent Reach (π₋ᵢ)      : {:.6}", opp_cf_reach);
		trace!(
			"  Action {:<2}: v(I,a)={:<12.6} | ΔRegret={:<12.6}",
			a_idx,
			action_value,
			regret_delta
		);
	} else {
		// Original trace logging
		if vr_ready {
			trace!("[REGRET_UPDATE_VR] Key={:?}, Action={}, v(I,a)={:.6}, B(I)={:.6}, π₋ᵢ={:.6}, ΔRegret={:.6}",
                   infoset_key, a_idx, action_value, reference_value, opp_cf_reach, regret_delta);
		} else {
			trace!("[REGRET_UPDATE] Key={:?}, Action={}, v(I,a)={:.6}, EV(I)={:.6}, π₋ᵢ={:.6}, ΔRegret={:.6}",
                   infoset_key, a_idx, action_value, reference_value, opp_cf_reach, regret_delta);
		}
	}
}

/// Logs the details of an average strategy update calculation either at INFO or TRACE level.
#[inline]
pub fn log_avg_strat_update_details(
	a_idx: usize,
	sigma: Prob,
	strat_increment: Prob,
	should_log_instrumented: bool,
) {
	if should_log_instrumented {
		trace!(
			"  Action {:<2}: strategy={:<12.6} | ΔStratNum={:<12.6}",
			a_idx,
			sigma,
			strat_increment
		);
	} else {
		trace!(
			"    Action {}: strategy={:.6}, ΔStratNum = {:.6}",
			a_idx,
			sigma,
			strat_increment
		);
	}
}

/// Logs the header for the average strategy update if instrumented.
#[inline]
pub fn log_avg_strat_header(
	_infoset_key: InfosetHashKey, // Renamed as it's not used directly in this version for the main log
	opp_cf_reach: Prob,
	avg_strat_weight: Prob,
	should_log_instrumented: bool,
	iter_count: u64, // Changed to u64
	linear_weighting: bool,
	approx_denominator_sum_before_update: f64,
) {
	if should_log_instrumented {
		trace!("[INSTRUMENT_LOG] Avg-Strategy Update (Iter={})", iter_count);
		trace!("  Opponent Reach (π₋ᵢ) : {:.6}", opp_cf_reach);
		trace!(
			"  Iteration Weight  : {:.1}",
			if linear_weighting {
				iter_count as f64
			} else {
				1.0
			}
		);
		trace!("  Avg Strat Weight  : {:.6}", avg_strat_weight);
	} else {
		trace!("  -> Calculated avg_strat_weight = {:.6}", avg_strat_weight);
		trace!(
			"  -> Added {:.6} to reach denominator (New total: {:.6})",
			avg_strat_weight,
			approx_denominator_sum_before_update // Use passed value
		);
	}
}

/// Logs the footer for the average strategy update if instrumented.
#[inline]
pub fn log_avg_strat_footer(infoset_key: InfosetHashKey, should_log_instrumented: bool) {
	if !should_log_instrumented {
		// Only trace if not instrumented logging
		trace!("[AVG_STRAT_ACCUM] Finished for Key={:?}", infoset_key);
	}
}

/// Logs detailed information after the recursion loop in `handle_player_node`.
#[inline]
pub fn log_player_node_post_recursion(
	state_as_string: String,
	infoset_key: InfosetHashKey,
	node_value: Utility,
	action_values: &[f64; MAX_GRID],
	num_actions: usize,
	row: &regretmap::Row,
	should_log_instrumented: bool,
	iter_count: u64,
	vr_ready: bool,
) {
	// --- Log State AFTER Recursion (Instrumented) ---
	if should_log_instrumented {
		trace!(
			"[INSTRUMENT_LOG] State AFTER recursion loop:\n{}",
			state_as_string
		);
	}
	// --- End Log State AFTER Recursion ---

	trace!(
		"[TRAVERSER_POST_LOOP] Key={:?}, NodeValue(EV(I))={:.6}",
		infoset_key,
		node_value
	);
	// Format the slice manually for logging
	let action_values_str = action_values[..num_actions]
		.iter()
		.map(|&v| format!("{:.6}", v))
		.collect::<Vec<_>>()
		.join(", ");
	trace!("  ActionValues: [{}]", action_values_str); // Log computed action values

	// --- Log Row state BEFORE update ---
	log_row_state(
		"BEFORE",
		row,
		infoset_key,
		should_log_instrumented,
		iter_count,
		vr_ready,
	);
	// --- End Log Row state BEFORE update ---

	// --- Log Action Values and Node Value for Instrumented Key ---
	if should_log_instrumented {
		trace!("[INSTRUMENT_LOG] Calculated Values:");
		trace!("  Node Value (EV(I))         : {:.6}", node_value);
		for (i, &action_val) in action_values.iter().enumerate().take(num_actions) {
			trace!(
				"  Action {:<2} Value (v(I,a))   : {:.6}",
				i,
				action_val
			);
		}
	}
	// --- End Log Action Values ---
}

/// Logs opponent action sampling and updates sampling counts when the log_opponent_sampling flag is set.
#[inline]
pub fn log_opponent_action_sampling(
	opponent_key: InfosetHashKey,
	legal_mask: u32,
	current_strategy: &[f64; MAX_GRID],
	sampled_idx: u8,
	_sampled_prob: f64, // _prefix as sampled_prob is not used in this specific logging function body
	opponent_sampling_counts: &DashMap<InfosetHashKey, DashMap<u8, AtomicUsize>>,
) {
	let _strategy_str = (0..32) // Prefixed with _
		.filter(|&i| (legal_mask & (1 << i)) != 0)
		.map(|i| format!("A{}:{:.4}", i, current_strategy[i as usize]))
		.collect::<Vec<_>>()
		.join(", ");
	// trace!( // Original debug! was commented out, keeping as trace! if re-enabled
	//     "[OPP_SAMPLE_LOG] Opponent Key={:?}, Strategy=[{}], Sampled Idx={}, Prob={:.4}",
	//     opponent_key, _strategy_str, sampled_idx, _sampled_prob
	// );

	// Update global counts
	let action_counts = opponent_sampling_counts.entry(opponent_key).or_default();
	action_counts
		.entry(sampled_idx)
		.or_insert_with(|| AtomicUsize::new(0)) // Use or_insert_with for clarity
		.fetch_add(1, AtomicOrdering::Relaxed);
}

/// Checks if the given infoset key requires instrumentation, performs any needed logging,
/// and returns appropriate flags for further processing.
#[inline]
pub fn check_instrumentation(
	infoset_key: InfosetHashKey,
	legal_mask: u32,
	current_strategy: &[f64; MAX_GRID],
	instrumented_key_opt: Option<InfosetHashKey>,
	instrument_log_config_opt: &Option<(usize, AtomicUsize)>,
) -> (bool, bool) {
	let mut should_log_instrumented = false; // Make mutable
	let mut next_log_opponent_sampling = false; // Flag for recursive calls - Keep mut as it's assigned below

	// Removed early return: return (true, true);

	// Check if this is the instrumented key
	if let (Some(target_key), Some((freq, counter))) =
		(instrumented_key_opt, instrument_log_config_opt)
	{
		if infoset_key == target_key {
			// Set flag to log opponent nodes visited *after* this one
			next_log_opponent_sampling = true;
			// --- Original instrumentation logging logic ---
			let current_count = counter.fetch_add(1, AtomicOrdering::Relaxed);
			if (current_count + 1) % *freq == 0 {
				should_log_instrumented = true;
			}
		}
	}

	// Log bit order and initial strategy if needed
	if should_log_instrumented {
		let bit_order: Vec<_> = (0..32)
			.filter(|&i| (legal_mask & (1 << i)) != 0)
			.collect();
		trace!(
			"[INSTRUMENT_LOG] Key {:?} BitIter order = {:?}",
			infoset_key,
			bit_order
		);
		// Assuming Kuhn Poker (max 2 actions) for this specific log format.
		// Adjust if needed for games with more actions.
		if legal_mask.count_ones() <= 2 && MAX_GRID >= 2 {
			trace!(
				"[INSTRUMENT_LOG] Initial σ(I) = [ActionIdx 0: {:.6}, ActionIdx 1: {:.6}]",
				current_strategy[0],
				current_strategy[1]
			);
		} else {
			// Generic log for more actions
			let strategy_str = (0..32)
				.filter(|&i| (legal_mask & (1 << i)) != 0)
				.map(|i| format!("Idx {}: {:.6}", i, current_strategy[i as usize]))
				.collect::<Vec<_>>()
				.join(", ");
			trace!("[INSTRUMENT_LOG] Initial σ(I) = [{}]", strategy_str);
		}
	}

	(should_log_instrumented, next_log_opponent_sampling)
}

// --- New Logging Helpers ---

#[inline]
pub fn log_terminal_node_details(player_to_update: PlayerId, utility: Utility, _state_str: &str) {
	trace!(
		"[ES_CFR_DEBUG] Terminal state reached. Utility for P{}: {}",
		player_to_update,
		utility
	);
	// trace!("Terminal game state:\n{}", state_str);
}

#[inline]
pub fn log_chance_node_sample(
	sampled_action: ConcreteAction,
	sampled_prob: Prob,
	player_reach: Prob,
	opp_cf_reach: Prob,
) {
	trace!(
        "  [CHANCE] Sampled Action {:?} (Prob {:.3e}). Recursing with πᵢ={:.3e}, π₋ᵢ={:.3e} * {:.3e} = {:.3e}",
        sampled_action, sampled_prob, player_reach, opp_cf_reach, sampled_prob, opp_cf_reach * sampled_prob
    );
}

#[inline]
pub fn log_chance_node_return(adjusted_util: Utility) {
	trace!("  [CHANCE] Returned Utility: {:.6}", adjusted_util);
}

#[inline]
pub fn log_escfr_node_entry(
	_depth: usize,
	_current_player: PlayerId,
	_player_to_update: PlayerId,
	_infoset_key: InfosetHashKey,
	_legal_mask: u32,
	_player_reach: Prob,
	_opp_cf_reach: Prob,
	_state_str: &str,
) {
	// trace!(
	//     "[ES_CFR_NODE_ENTRY] Depth={}, Player={}, Traverser={}, Key={:?}, Mask={:b}, πᵢ={:.3e}, π₋ᵢ={:.3e}\nState:\n{}",
	//     depth, current_player, player_to_update, infoset_key, legal_mask, player_reach, opp_cf_reach, state_str
	// );
}

#[inline]
pub fn log_opponent_action_application(
	sampled_abstract_action: ConcreteAction,
	sampled_prob: Prob,
	sampled_idx: u8,
	player_reach: Prob,
	opp_cf_reach: Prob,
) {
	trace!(
        "  [OPPONENT] Sampled Action {:?} (Prob {:.3e}, Idx {}). Recursing with πᵢ={:.3e}, π₋ᵢ={:.3e} * {:.3e} = {:.3e}",
        sampled_abstract_action, sampled_prob, sampled_idx, player_reach, opp_cf_reach, sampled_prob, opp_cf_reach * sampled_prob
    );
}

#[inline]
pub fn log_opponent_node_entry(current_player: PlayerId, player_to_update: PlayerId) {
	trace!(
		"  [OPPONENT] Handling node for P{} (Traverser is P{})",
		current_player,
		player_to_update
	);
}

#[inline]
pub fn log_opponent_node_child_return(child_util: Utility) {
	trace!("  [OPPONENT] Returned Child Utility: {:.6}", child_util);
}

#[inline]
pub fn log_opponent_node_adjusted_return(adjusted_util: Utility) {
	trace!(
		"  [OPPONENT] Adjusted (baseline) Utility returned to parent: {:.6}",
		adjusted_util
	);
}

#[inline]
pub fn log_traverser_action_recurse(
	action: ConcreteAction,
	action_prob: Prob,
	player_reach: Prob,
	next_player_reach: Prob,
	opp_cf_reach: Prob,
) {
	trace!(
        "  [TRAVERSER] Recursing: Action {:?} (Prob {:.3e}), Next πᵢ = {:.3e} * {:.3e} = {:.3e}, π₋ᵢ = {:.3e}",
        action, action_prob, player_reach, action_prob, next_player_reach, opp_cf_reach
    );
}

#[inline]
pub fn log_traverser_action_return(action: ConcreteAction, utility: Utility) {
	trace!(
		"  [TRAVERSER] Action {:?} Returned Utility: {:.6}",
		action,
		utility
	);
}

#[inline]
pub fn log_player_node_pre_recursion(state_as_string: &str, should_log_instrumented: bool) {
	if should_log_instrumented {
		trace!(
			"[INSTRUMENT_LOG] State BEFORE recursion loop:\n{}",
			state_as_string
		);
	}
}

#[inline]
pub fn log_player_node_final_return(
	infoset_key: InfosetHashKey,
	return_util: Utility,
	vr_ready: bool,
) {
	trace!(
		"[TRAVERSER_RETURN] Key={:?}, Returning {:.6} (baseline-enhanced={})",
		infoset_key,
		return_util,
		vr_ready
	);
}

// --- End New Logging Helpers ---

/// Enable detailed logging for a specific infoset key every `freq` times it's encountered.
/// This function is intended to be called to configure an ExternalSamplingCfr instance.
pub fn instrument_key(
	instrumented_key_field: &mut Option<InfosetHashKey>,
	instrument_log_config_field: &mut Option<(usize, AtomicUsize)>,
	key_to_instrument: InfosetHashKey,
	freq: usize,
) {
	if freq == 0 {
		warn!("Instrumentation frequency cannot be 0. Disabling instrumentation.");
		*instrumented_key_field = None;
		*instrument_log_config_field = None;
	} else {
		info!(
			"Instrumenting key {:?} with frequency {}",
			key_to_instrument, freq
		);
		*instrumented_key_field = Some(key_to_instrument);
		// Initialize counter to 0
		*instrument_log_config_field = Some((freq, AtomicUsize::new(0)));
	}
}

/// Prints a table summarizing the current state of the policy table from an InfoStatesMap.
/// Useful for debugging convergence issues. This is a wrapper around the function in `es_util`.
#[allow(dead_code)]
pub fn print_policy_audit_table(info_states: &InfoStatesMap) {
	es_util::print_policy_audit_table(info_states);
}

/// Prints a report summarizing the observed opponent action sampling distributions.
pub fn print_opponent_sampling_report(
	opponent_sampling_counts: &DashMap<InfosetHashKey, DashMap<u8, AtomicUsize>>,
) {
	println!("\n--- Opponent Action Sampling Report ---");
	if opponent_sampling_counts.is_empty() {
		println!("No opponent sampling data collected (was logging enabled for relevant nodes?).");
		return;
	}

	let mut sorted_keys: Vec<_> = opponent_sampling_counts
		.iter()
		.map(|entry| *entry.key())
		.collect();
	sorted_keys.sort(); // Sort by key for consistent output

	println!(
		"{:<10} | {:<10} | {:<15} | {:<15}",
		"OpponentKey", "ActionIdx", "SampleCount", "EmpiricalProb"
	);
	println!("{:-<10}+{:-<10}+{:-<15}+{:-<15}", "", "", "", "");

	for key in sorted_keys {
		if let Some(action_map_ref) = opponent_sampling_counts.get(&key) {
			let action_map = action_map_ref.value();
			let total_samples: usize = action_map
				.iter()
				.map(|entry| entry.value().load(AtomicOrdering::Relaxed))
				.sum();

			if total_samples == 0 {
				continue;
			} // Skip if no samples for this key

			let mut sorted_actions: Vec<_> = action_map
				.iter()
				.map(|entry| (*entry.key(), entry.value().load(AtomicOrdering::Relaxed)))
				.collect();
			sorted_actions.sort_by_key(|(idx, _)| *idx); // Sort by action index

			for (action_idx, count) in sorted_actions {
				let empirical_prob = count as f64 / total_samples as f64;
				println!(
					"{:<10} | {:<10} | {:<15} | {:<15.6}",
					key.0, action_idx, count, empirical_prob
				);
			}
			println!("{:-<10}+{:-<10}+{:-<15}+{:-<15}", "", "", "", ""); // Separator between keys
		}
	}
	println!("--- End Opponent Action Sampling Report ---");
}

/// Logs regret update details and checks if the regret delta is valid.
/// Panics if regret_delta is not finite.
#[inline]
pub fn log_regret_updates_and_check_validity(
	infoset_key: InfosetHashKey,
	a_idx: usize,
	action: ConcreteAction,
	action_values: &[f64; MAX_GRID],
	reference_value: f64,
	regret_delta: f64,
	opp_cf_reach: Prob,
	should_log_instrumented: bool,
	vr_ready: bool,
) {
	// Log detailed update info by calling the existing helper within this module
	log_regret_update_details(
		infoset_key,
		a_idx,
		action_values[a_idx],
		reference_value,
		regret_delta,
		opp_cf_reach,
		should_log_instrumented,
		vr_ready,
	);

	if !regret_delta.is_finite() {
		panic!("NaN/Inf detected in regret update for key {:?}, action {:?} (regret_delta={:.2}). Skipping update.",
            infoset_key,
            action,
            regret_delta,
        );
	}
}

```

crates/algorithms/src/es_solver.rs:
```
use crate::external_sampling_cfr::ExternalSamplingCfr; // Removed unused es_util import
use cfr_rng::CfrRngPool;
use engine::{
	abstraction::InformationAbstraction, // Removed ActionAbstraction and IdentityAbstraction
	game::Game,
	policy::{PackedPolicy, TabularPolicy},
	solver::{PlayerAwareSolver, Solver},
	state::State,
	types::PlayerId,
};
use log::{error, warn};
use std::sync::Arc;

// Implement Solver trait for ExternalSamplingCfr
impl<G> Solver<G> for ExternalSamplingCfr<G>
where
	G: Game + 'static,
	G::State: State<Game = G> + 'static,
{
	fn run_iteration(&mut self, _rng_pool: &CfrRngPool) {
		// Use CfrRngPool
		self.iter_count += 1;
		// Note: InfoStatesMap iteration counter is now incremented by BaseTrainer
		// to ensure consistency between single and multi-threaded modes

		// Note: update_unpruning is now called in mark_iteration to avoid multi-thread conflicts

		for p in 0..self.game.num_players() {
			self.run_one_traversal(p as PlayerId);
		}
	}

	fn average_policy(&self) -> Arc<TabularPolicy<G>> {
		let mut policy = TabularPolicy::new(
			self.abstraction.clone() as Arc<dyn InformationAbstraction<G>>,
			true
		);

		for (key, row_arc) in self.info_states().iter() {
			// Changed to use info_states()
			let row = &*row_arc;
			let packed = row.get_average_policy(Some(key)).unwrap_or_else(|e| {
				error!("Error generating average policy for key {:?}: {}", key, e);
				PackedPolicy {
					num_actions: 0,
					probabilities: Default::default(),
				}
			});
			policy.set_packed_policy(key, packed);
		}

		Arc::new(policy)
	}

	fn current_policy(&self) -> Arc<TabularPolicy<G>> {
		let mut policy = TabularPolicy::new(
			self.abstraction.clone() as Arc<dyn InformationAbstraction<G>>,
			true
		); // Enable uniform fallback for unvisited states
											 // Iterate over the Arc<ShardedTable>
		for (key, row_arc) in self.info_states().iter() {
			// Changed to use info_states()
			let values = &*row_arc; // Dereference Arc<Row> to &Row
			let current_policy_for_key = if self.config.perturb_strategy {
				values.get_current_policy_perturbed().unwrap_or_else(|e| {
					error!("Error generating current policy for key {:?}: {}", key, e);
					PackedPolicy {
						num_actions: 0,
						probabilities: Default::default(),
					}
				})
			} else {
				values.get_current_policy().unwrap_or_else(|e| {
					error!("Error generating current policy for key {:?}: {}", key, e);
					PackedPolicy {
						num_actions: 0,
						probabilities: Default::default(),
					}
				})
			};
			policy.set_packed_policy(key, current_policy_for_key);
		}
		Arc::new(policy)
	}

    fn num_info_states(&self) -> usize {
        self.info_states().iter().len()
    }


	fn as_any(&self) -> &dyn std::any::Any {
		self
	}
	fn as_any_mut(&mut self) -> &mut dyn std::any::Any {
		self
	}

}

// Implement PlayerAwareSolver for ExternalSamplingCfr
impl<G> PlayerAwareSolver<G> for ExternalSamplingCfr<G>
where
	G: Game + 'static,
	G::State: State<Game = G> + 'static,
{
	/// Runs one iteration, updating only the specified `player`.
	/// If `player` is `None`, chooses a player uniformly at random using the provided `rng_pool`.
	fn run_iteration_for_player(&mut self, player: Option<PlayerId>, rng_pool: &CfrRngPool) {
		// Accept CfrRngPool
		if let Some(p) = player {
			// Caller requested a specific player update – run exactly one traversal.
			self.run_one_traversal(p);
		} else {
			// Default behaviour: update exactly one randomly chosen player.
			// Use the provided rng_pool for this top-level sampling decision.
			let num_players = self.game.num_players();
			if num_players > 0 {
				let player_to_update = rng_pool.gen_range(0..num_players) as PlayerId; // Use rng_pool
				self.run_one_traversal(player_to_update); // Perform exactly one traversal
			} else {
				// Handle the case of zero players gracefully, though unlikely.
				warn!("run_iteration_for_player called with None player on a game with 0 players.");
			}
		}
	}

	fn mark_iteration(&mut self, global_iteration: u64) {
		self.iter_count = global_iteration; // Cast u64 to usize for internal counter
		
		// With hybrid lazy approach, unpruning happens naturally when
		// current_iter >= revisit_at, so no explicit unpruning needed
	}
}

```

crates/algorithms/src/es_util.rs:
```
use cfr_rng::CfrRngPool; // Import CfrRngPool
use itertools::Itertools;
use log::error;
use regretmap::InfoStatesMap;
use regretmap::Row;
use std::sync::Arc;

use engine::types::MAX_GRID;

// Removed merge_rules import
// Removed rayon import
use engine::types::{ConcreteAction, InfosetHashKey};
use engine::{policy::PackedPolicy, state::State};
// Removed DELTA_MAX, PRUNE_SKIP_PROB, WARMUP_TRAVERSALS
// Removed unused: use crate::scratch_buffers::ScratchBuffers;
// Removed unused rand import

/// Computes the node value and the regret–deltas for every action.
/// If `use_baseline` == true the per-action EMA baselines are updated.
/// Returns `(node_value , deltas)`.
/*
pub fn compute_deltas_and_update_baselines(
		mask        : u32,         // +++ Use mask +++
		sigmas      : &[f64; MAX_GRID],   // σ(I)
		action_vals : &[f64; MAX_GRID],   // Q̂(I,a) for all a
		row         : &Row,               // Use the refactored Row
		use_baseline: bool,               // +++ Keep baseline flag +++
) -> (f64, [f64; MAX_GRID]) {
	let mut node_v = 0.0;
	for idx in 0..row.num_actions as usize {
		node_v += sigmas[idx] * action_vals[idx];
	}

	let mut deltas = [0.0; MAX_GRID];
	for idx in 0..row.num_actions as usize {
		let baseline = if use_baseline {
			row.baseline_action_values[idx].get()
		} else {
			node_v
		};
		deltas[idx] = action_vals[idx] - baseline;

		if use_baseline {
			row.update_baseline_ema(idx, action_vals[idx]);
		}
	}
	(node_v, deltas)
}
*/

/// Pretty-prints a slice of `f64` with fixed precision in scientific format.
pub fn format_f64_slice(slice: &[f64], prec: usize) -> String {
	slice
		.iter()
		.map(|v| format!("{:.prec$e}", v, prec = prec))
		.join(", ")
}

/// Pretty-prints a PackedPolicy with fixed precision.
pub fn format_policy(policy: &PackedPolicy, prec: usize) -> String {
	policy.probabilities[..policy.num_actions as usize]
		.iter()
		.enumerate()
		.map(|(idx, &prob)| format!("A{}:{:.prec$}", idx, prob, prec = prec))
		.join(", ")
}

/// Utility dump of the current table contents.  
/// Intended for occasional human diagnostics, *not* hot-path logging.
pub fn print_policy_audit_table(map: &InfoStatesMap) {
	println!("\n--- Policy Audit Table (External-Sampling variants) ---");
	let mut rows: Vec<(InfosetHashKey, Arc<Row>)> = map.iter();
	rows.sort_by_key(|(k, _)| *k);

	println!(
		"{:<8} | {:<10} | {:<30} | {:<30} | {:<12} | {:<30}",
		"Key", "Visits", "Regrets", "CumPolNum", "ReachDen", "AvgPolicy"
	);
	println!(
		"{:-<8}+{:-<10}+{:-<30}+{:-<30}+{:-<12}+{:-<30}",
		"", "", "", "", "", ""
	);

	for (key, row) in rows {
		// Use num_actions to get number of actions
		let n = row.num_actions as usize;
		if n == 0 {
			continue;
		}

		let rgt = format_f64_slice(
			&(0..n)
				.map(|i| row.cumulative_regrets[i].get())
				.collect::<Vec<_>>(),
			2,
		);
		let cnum = format_f64_slice(
			&(0..n)
				.map(|i| row.cumulative_policy_numerator[i].get())
				.collect::<Vec<_>>(),
			2,
		);
		let den = format!("{:.4e}", row.cumulative_reach_denominator_sum.get());
		let avg = row.get_average_policy(Some(key)).unwrap_or_else(|e| {
			error!(
				"Error generating average policy for key {:?} in audit table: {}",
				key, e
			);
			PackedPolicy::new(0, &[])
		});
		let avg_s = format_policy(&avg, 3);
		let visits = row.num_updates.load(std::sync::atomic::Ordering::Relaxed);

		println!(
			"{:<8} | {:<10} | [{:<28}] | [{:<28}] | {:<12} | [{:<28}]",
			key.0, visits, rgt, cnum, den, avg_s
		);
	}

	println!(
		"{:-<8}+{:-<10}+{:-<30}+{:-<30}+{:-<12}+{:-<30}",
		"", "", "", "", "", ""
	);
	println!("--- End Policy Audit Table ---");
}

/// Samples one index from `probs` using direct indexing.
/// Assumes `probs` sum ≈ 1 over the first `num_actions` indices.
/// Incorporates an epsilon-greedy exploration strategy.
/// Falls back to the last valid index if FP error occurs during weighted sampling.
pub fn sample_action_index(
	key: InfosetHashKey,
	num_actions: usize,
	probs: &[f64; MAX_GRID],
	rng_pool: &CfrRngPool,
	log_this: bool,
	exploration_rate: f64,
) -> u8 {
	if num_actions == 0 {
		panic!(
			"sample_action_index called with zero actions for key {:?}",
			key
		);
	}

	let explore_roll: f64 = rng_pool.next_f64_open01();

	let result_idx: u8;
	let source: &str;
	let random_val: f64;
	let mut fallback_used = false;

	if explore_roll < exploration_rate {
		// --- Explore: Choose a random legal action uniformly ---
		source = "Explore";
		random_val = explore_roll;
		result_idx = rng_pool.gen_range(0..num_actions) as u8;
	} else {
		// --- Exploit: Sample according to the provided strategy ---
		source = "Strategy";
		let z: f64 = rng_pool.next_f64_open01();
		random_val = z;
		let mut acc = 0.0;
		let mut chosen_idx: Option<u8> = None;

		for (i, &p) in probs.iter().enumerate().take(num_actions) {
			if p < 0.0 {
				log::warn!(
					"Negative probability encountered in sample_action_index: p={}, index={}",
					p,
					i
				);
				continue;
			}
			acc += p;
			if z < acc || (acc - 1.0).abs() < 1e-9 {
				chosen_idx = Some(i as u8);
				break;
			}
		}

		result_idx = match chosen_idx {
			Some(idx) => idx,
			None => {
				// Fallback for weighted sampling
				fallback_used = true;
				log::warn!("Weighted sampling fallback triggered for num_actions {}. Probs sum might not be 1.0 or FP error. (acc={}, z={})", num_actions, acc, z);
				(num_actions - 1) as u8
			}
		};
	}

	if log_this {
		// Format the probability distribution string for all actions
		let dist_str = (0..num_actions)
			.map(|i| format!("A{}:{:.4}", i, probs[i]))
			.collect::<Vec<_>>()
			.join(", ");

		log::trace!(
            "[SAMPLE_ACTION] Key={:?}, Dist=[{}], Source={}, RndVal={:.6}, ResultIdx={}, Fallback={}",
            key, dist_str, source, random_val, result_idx, fallback_used
        );
	}

	result_idx
}

// ------------------------------------------------------------------
// Stochastic RBP helper
// ------------------------------------------------------------------
/// Returns `true` if a pruned action should be skipped this time.
/*
#[inline]
pub fn should_stochastically_prune(is_pruned: bool, rng: &mut dyn RngCore) -> bool {
	is_pruned && rng.gen::<f64>() < PRUNE_SKIP_PROB
}
*/
// --- ScratchBuffers struct and methods removed from here ---
// --- They are now in src/scratch_buffers.rs ---
use engine::solver_config::{DiscountMode, SolverConfig, VRMode};

// --- Solver Config Helper Functions ---

#[inline]
pub fn check_is_linear_weighting(config: &SolverConfig) -> bool {
	config.discount_mode == DiscountMode::Linear
}

#[inline]
pub fn check_is_vr(config: &SolverConfig) -> bool {
	config.vr_mode != VRMode::None
}

#[inline]
pub fn check_is_vr_ema(config: &SolverConfig) -> bool {
	config.vr_mode == VRMode::Ema
}

#[inline]
pub fn check_is_vr_mean(config: &SolverConfig) -> bool {
	config.vr_mode == VRMode::Mean
}

#[inline]
pub fn check_is_perturb_strategy(config: &SolverConfig) -> bool {
	config.perturb_strategy
}

// --- End Solver Config Helper Functions ---

// ------------------------------------------------------------------
// Legacy helper used by some integration tests – wraps the engine
// `State::sample_chance_action` method with the previous name and order.
// This keeps the tests readable without touching core crates.
// ------------------------------------------------------------------

/// Thin wrapper that forwards to `State::sample_chance_action`.
/// Returns the sampled `ConcreteAction` and its probability (if any).
pub fn sample_chance<G>(state: &G::State, rng_pool: &CfrRngPool) -> Option<(ConcreteAction, f64)>
where
	G: engine::game::Game,
	G::State: State<Game = G>,
{
	state.sample_chance_action(rng_pool)
}

```

crates/algorithms/src/external_sampling_cfr.rs:
```
#![allow(missing_docs)]
//! External-Sampling MCCFR with uniform iteration weighting (vanilla CFR).
//! Traversal pattern identical to the linear-weighted solver, but **no**
//! per-iteration weight factor is applied.
//!
//! Critical ES-CFR fixes applied:
//! 1. Regret updates MUST be weighted by opponent counterfactual reach π_{-i}(h)
//! 2. Average strategy updates use the ACTING player's reach, not the traverser's reach
//!
//! First paper to get base ES MC CFR down
//! AE - Monte Carlo Sampling for Regret Minimization in Extensive Games
//! re: Marc Lanctot https://proceedings.neurips.cc/paper_files/paper/2009/file/00411460f7c92d2124a67ea0f4cb5f85-Paper.pdf

use cfr_rng::CfrRngPool;
use engine::abstraction::InformationAbstraction;
use engine::game::Game;
use crate::util::index_to_concrete_action;
// use engine::policy::{PackedPolicy, TabularPolicy}; // Unused
// use engine::solver::{PlayerAwareSolver, Solver}; // Unused
use engine::state::State;
use engine::types::{
	ConcreteAction, InfosetHashKey, PlayerId, Prob, Utility,
	CHANCE_PLAYER_ID, MAX_GRID,
};
use log::{debug, error, trace}; // Removed unused `info`
use regretmap::InfoStatesMap;
use std::sync::Arc;
use std::sync::atomic::Ordering;


// Removed es_instrumentation imports
use crate::es_util::{
    check_is_linear_weighting, check_is_vr, check_is_vr_ema, check_is_vr_mean,
    sample_action_index,
};
use crate::rbp::RBPManager;

#[cfg(feature = "profiling")]
pub mod profiling_timers {
    use std::sync::atomic::{AtomicU64, Ordering};

    pub static INFO_GATHER_NS: AtomicU64 = AtomicU64::new(0);
    pub static COMPUTE_STRAT_NS: AtomicU64 = AtomicU64::new(0);
    pub static HANDLE_OPP_NS: AtomicU64 = AtomicU64::new(0);
    pub static HANDLE_PLAYER_NS: AtomicU64 = AtomicU64::new(0);

    pub fn print_summary() {
        let ig = INFO_GATHER_NS.load(Ordering::Relaxed);
        let cs = COMPUTE_STRAT_NS.load(Ordering::Relaxed);
        let ho = HANDLE_OPP_NS.load(Ordering::Relaxed);
        let hp = HANDLE_PLAYER_NS.load(Ordering::Relaxed);
        // println!("=== escfr_recursive Profiling Summary ===");
        // println!("info_gather total: {:.3} ms", ig as f64 / 1e6);
        // println!("compute_current_strategy total: {:.3} ms", cs as f64 / 1e6);
        // println!("handle_opponent_node total: {:.3} ms", ho as f64 / 1e6);
        // println!("handle_player_node total: {:.3} ms", hp as f64 / 1e6);
    }
}
									 // Removed unused DiscountMode, VRMode imports

/// Holds an Arc to the shared `ShardedTable` (aliased as `InfoStatesMap`).
/// Uses uniform (unweighted) iteration averaging.
pub struct ExternalSamplingCfr<G: Game> {
	pub(crate) game: Arc<G>,
	pub(crate) abstraction: Arc<dyn InformationAbstraction<G>>,
	pub(crate) info_states: Arc<InfoStatesMap>,
	pub(crate) rng_pool: CfrRngPool, // Use CfrRngPool instead of StdRng
	pub(crate) config: engine::solver_config::SolverConfig, // <-- CHANGE THIS LINE

	pub(crate) iter_count: u64, // global iteration count

	pub(crate) vr_ready: bool, // For VR, starts as true toggles to false when WARMING_UP is false

	pub(crate) warming_up: bool, // For VR, starts as true toggles to false when WARMING_UP is false

	// --- Instrumentation removed for performance ---

	// --- RBP Manager ---
	pub(crate) rbp_manager: Option<Arc<RBPManager>>,
	
	// --- Depth limiting for search ---
	pub(crate) max_depth: Option<usize>,
	
	// --- Infostate Hook ---
	pub(crate) infostate_hook: Option<Box<dyn crate::infostate_hook::InfostateHook>>,
}

// Constructors are now in src/es_factory.rs

impl<G> ExternalSamplingCfr<G>
where
	G: Game + 'static,
	G::State: State<Game = G> + 'static,
{
	/// Returns the number of rows currently held in the scratch buffer's local table.
	#[allow(dead_code)]
	pub fn scratch_local_len(&self) -> usize {
		0
	}

	/// Set the RBP manager for this solver
	pub fn set_rbp_manager(&mut self, rbp_manager: Arc<RBPManager>) {
		self.rbp_manager = Some(rbp_manager);
	}

	/// Get a reference to the RBP manager if it exists
	pub fn rbp_manager(&self) -> Option<&Arc<RBPManager>> {
		self.rbp_manager.as_ref()
	}
	
	/// Set the maximum depth for traversal (used in depth-limited search)
	pub fn set_max_depth(&mut self, max_depth: Option<usize>) {
		self.max_depth = max_depth;
	}
	
	/// Set the infostate hook for this solver
	pub fn set_infostate_hook(&mut self, hook: Box<dyn crate::infostate_hook::InfostateHook>) {
		self.infostate_hook = Some(hook);
	}

	/// Get the current iteration count
	pub fn iter_count(&self) -> u64 {
		self.iter_count
	}


	/// Computes the current strategy for the given infoset key and legal mask.
	/// Returns the strategy in a fixed-size array.
	#[inline]
	fn compute_current_strategy(
		&mut self, // <-- CHANGED &self to &mut self
		infoset_key: InfosetHashKey,
		num_actions: usize,
	) -> [f64; MAX_GRID] {
		let mut current_strategy = [0.0; MAX_GRID];

		// For now, skip pruning to remove mask dependency
		// TODO: Update RBP to work with direct indexing
		
		self.info_states().with_row(infoset_key, num_actions, |row| {
			// Debug check: ensure the number of actions matches
			#[cfg(debug_assertions)]
			{
				let expected_num_actions = num_actions as u8;
				if row.num_actions != expected_num_actions {
					panic!(
						"GI-11 VIOLATION / ACTION COUNT INCONSISTENCY: InfosetKey {:?}\n\
						 Row's established num_actions: {}\n\
						 Current state's legal actions count: {}\n\
						 This means different states mapping to the same infoset key have different numbers of legal actions.",
						infoset_key, row.num_actions, expected_num_actions
					);
				}
			}

			// Debug logging for strategy computation
			if log::log_enabled!(log::Level::Debug) {
				let regrets: Vec<f64> = (0..num_actions)
					.map(|i| row.cumulative_regrets[i].get())
					.collect();
				log::debug!(
					"\n[STRATEGY COMPUTE] Infoset: {} | Actions: {}",
					infoset_key.0, num_actions
				);
				log::debug!(
					"  Regrets: {:?}",
					regrets
				);
			}

			if self.config.perturb_strategy {
				// Directly compute sigma into the stack array, avoiding Vec allocation.
				row.write_current_strategy_perturbed(row.num_actions as usize, &mut current_strategy);
			}
			else {
				// Directly compute sigma into the stack array, avoiding Vec allocation.
				row.write_current_strategy_into(row.num_actions as usize, &mut current_strategy);
			}

			// Debug logging for resulting strategy
			if log::log_enabled!(log::Level::Debug) {
				let strategy: Vec<f64> = (0..num_actions)
					.map(|i| current_strategy[i])
					.collect();
				log::debug!(
					"  Strategy: {:?}",
					strategy
				);
			}
		});

		// Verify strategy sums to 1.0 (only for active actions)
		let sigma_sum: f64 = (0..num_actions)
			.map(|i| current_strategy[i])
			.sum();
		debug_assert!(
			num_actions == 0 || (sigma_sum - 1.0).abs() < 1e-9,
			"current_strategy(I) not normalised: sum={:.12} at key {:?} num_actions {}",
			sigma_sum,
			infoset_key,
			num_actions
		);

		current_strategy
	}

	/// Returns the number of rows currently held in the scratch vectors.
	#[allow(dead_code)]
	pub fn scratch_len(&self) -> usize {
		0
	}

	pub fn set_warmed_up(&mut self) {
		if self.warming_up {
			debug!("ES-CFR: VR enabled after warmup");
			self.warming_up = false;
			self.vr_ready = true;
		}
	}

	/// Immutable view of the underlying infoset table (`ShardedTable`).
	#[inline]
	pub fn info_states(&self) -> &InfoStatesMap {
		&self.info_states // Direct reference to Arc field
	}

	/// Runs a single vanilla ES-MCCFR traversal for the given player.
	pub(crate) fn run_one_traversal(&mut self, player_to_update: PlayerId) {
		let mut initial_state = self.game.new_initial_state(&mut self.rng_pool);
		self.run_one_traversal_from_state(&mut initial_state, player_to_update);
	}
	
	/// Run a traversal from a specific state (used for subgame solving)
	pub fn run_one_traversal_from_state(&mut self, state: &mut G::State, player_to_update: PlayerId) {
		self.info_states.increment_traversals(1);
		trace!("Running ES-CFR traversal for player {}", player_to_update);

		// Initialize all players' reach probabilities to 1.0
		// ATTEMPTED FIX (DIDN'T WORK): Allocate N+1 slots for chance reach tracking
		// We tried allocating N+1 slots (N for players, 1 for chance at index N) like Vanilla CFR does
		// Theory: ES-CFR was missing chance reach probability tracking
		// Result: Still only finds 928 infostates instead of 936, exploitability doesn't converge
		// Conclusion: The missing infostates bug is elsewhere in the ES-CFR implementation
		let mut reach_probabilities = vec![1.0; self.game.num_players() + 1];

		self.escfr_recursive(
			state,
			player_to_update,
			&mut reach_probabilities,
			0,
			false, // <-- Start with log_opponent_sampling = false
		);
	}

	fn handle_terminal_node(
		&mut self,
		state: &mut G::State,
		player_to_update: PlayerId,
	) -> Utility {
		let utilities = state.returns(); // Get returns for all players.
		if player_to_update >= utilities.len() {
			error!(
				"Player index {} out of bounds for returns vector (len {})", // Bounds check
				player_to_update,
				utilities.len()
			);
			return 0.0; // Return 0 on error
		}
		// Removed instrumentation: log_terminal_node_details
		utilities[player_to_update]// Return utility for the traverser
	}

	fn handle_chance_node(
		&mut self,
		state: &mut G::State,
		player_to_update: PlayerId,
		reach_probabilities: &mut [Prob],
		depth: usize,
		log_opponent_sampling: bool,
	) -> Utility {
		let (sampled_action, sampled_prob) = state
			.sample_chance_action(&self.rng_pool)
			.expect("chance node with no outcomes");

		// Removed instrumentation: log_chance_node_sample

		// Chance actions are already concrete, no conversion needed
		if let Err(e) = state.apply_action(sampled_action) {
			error!(
				"Error applying chance action {:?}: {}", // Use default formatting for ConcreteAction
				sampled_action.0,                              // Log the inner value
				e
			);
			return 0.0;
		}

		// In external sampling, only multiply OTHER players' reaches by chance probability
		// The player being updated is sampling, so their reach doesn't change
		let mut child_reaches = reach_probabilities.to_vec();
		let num_players = self.game.num_players();
		
		child_reaches[num_players] *= sampled_prob;
		
		let util = self.escfr_recursive(
			state,
			player_to_update,
			&mut child_reaches,
			depth + 1,
			log_opponent_sampling, // <-- Pass flag through chance node
		);

		// For chance nodes we simply pass the sampled return upward; any
		// baseline correction is handled in the parent infoset rows that
		// already exist for the real players.
		let adjusted_util = util;

		// Removed instrumentation: log_chance_node_return

		if let Err(e) = state.undo_last_action() {
			error!("undo_last_action failed after chance node: {}", e);
		}
		adjusted_util
	}

	/// Recursive External Sampling CFR traversal function.
	/// Calculates and returns the expected utility of the state *for the update_player*.
	/// Updates regrets and average strategy components *only* for the `update_player`.
	/// Samples actions for opponents and chance.
	pub fn escfr_recursive(
		// Changed visibility to pub
		&mut self,
		state: &mut G::State,
		player_to_update: PlayerId, // The player whose regrets/strategy we update in THIS traversal
		reach_probabilities: &mut [Prob], // Full array of reach probabilities for ALL players
		depth: usize,
		log_opponent_sampling: bool, // <-- Add flag parameter
	) -> Utility {
		// Debug logging for first few iterations
		if self.iter_count <= 5 && depth == 0 {
			trace!(
				"ES-CFR recursive - Player to update: {}, Initial reaches: {:?}", 
				player_to_update, reach_probabilities
			);
		}
		
		// Returns utility for the player_to_update
		// 1. Base Cases
		if state.is_terminal() {
			return self.handle_terminal_node(state, player_to_update);
		}
		
		// Check depth limit for search
		if let Some(max_depth) = self.max_depth {
			if depth >= max_depth {
				// Return heuristic value (0.0 for phase 1)
				return 0.0;
			}
		}

		let current_player = state.current_player();

		// Chance Node
		if current_player == CHANCE_PLAYER_ID {
			return self.handle_chance_node(
				state,
				player_to_update,
				reach_probabilities,
				depth,
				log_opponent_sampling,
			);
		}

		// trace!("ES-CFR: Reached non-chance node. Current player: {}, game state:\n{}", current_player, state.to_string()); // Covered by ENTRY log

       let infoset_key = self.abstraction.key(state, current_player);
       let legal_actions = state.legal_actions();
       let num_actions = legal_actions.len();

		// Log infoset key and state string at TRACE level
		trace!("ES-CFR: Infoset key: {:?}, State:\n{}", infoset_key, state.to_string());

		// Removed instrumentation: log_escfr_node_entry

		// Get the current strategy (current_strategy^t) using Regret Matching into a fixed-size array.
		let current_strategy = self.compute_current_strategy(infoset_key, num_actions);

		// Call infostate hook if present
		if let Some(ref hook) = self.infostate_hook {
			hook.on_infostate(
				infoset_key,
				state as &dyn std::any::Any,
				current_player,
				&legal_actions,
				&current_strategy[..num_actions],
			);
		}

		// Debug specific key
		let debug_key = infoset_key.0 == 0x01d76d6c53a310b7;
		if debug_key {
			// println!("\n[ES-CFR DEBUG] Hit key 0x{:016x} at iteration {}", infoset_key.0, self.iter_count);
			// println!("  Current player: {}, Traverser: {}", current_player, player_to_update);
			// println!("  Depth: {}, Num actions: {}", depth, num_actions);
			// println!("  Reach probabilities: {:?}", reach_probabilities);
			// println!("  Current strategy: {:?}", &current_strategy[..num_actions]);
		}

		// Branch on opponent vs. update_player
		if current_player != player_to_update {
			self.handle_opponent_node(
				depth,
				num_actions,
				state,
				player_to_update,
				reach_probabilities,
				&current_strategy,
				log_opponent_sampling,
			)
		} else {
			self.handle_player_node(
				infoset_key,
				depth,
				num_actions,
				state,
				player_to_update,
				reach_probabilities,
				&current_strategy,
				log_opponent_sampling,
			)
		}
	}

	/// Applies an opponent's sampled abstract action to the game state.
	/// Handles conversion to concrete action, validation, and logging.
	/// Returns true if action was successfully applied, false otherwise.
	#[inline]
	fn apply_opponent_action(
		&self,
		state: &mut G::State,
		sampled_idx: u8,
		_sampled_prob: f64,
		_player_reach: Prob,
		_opp_cf_reach: Prob,
	) -> Result<ConcreteAction, &'static str> {
		let legal_actions = state.legal_actions();
		let concrete_action: ConcreteAction =
			index_to_concrete_action(&legal_actions, sampled_idx as usize);

		// Debug assertion for concrete action legality
		#[cfg(debug_assertions)]
		{
			if !state.legal_actions().contains(&concrete_action) {
				panic!(
					"Opponent concrete action {:?} (from index {}) not legal in state:\n{}",
					concrete_action,
					sampled_idx,
					state.to_string()
				);
			}
		}

		if let Err(e) = state.apply_action(concrete_action) {
			error!(
				"Error applying sampled opponent action {:?}: {}",
				concrete_action,
				e
			);
			return Err("Failed to apply action");
		}

		// Removed instrumentation: log_opponent_action_application

		Ok(concrete_action)
	}

	/// Computes the adjusted utility for an opponent node using baseline-enhanced bootstrap.
	/// Handles both regular and variance-reduced utility adjustments.
	#[inline]
	fn compute_opponent_adjusted_utility(
		&mut self, // <-- CHANGED &self to &mut self
		opponent_key: InfosetHashKey,
		num_actions: usize,
		sampled_idx: u8,
		sampled_prob: f64,
		child_util: Utility,
	) -> Utility {
		// ---- Baseline-enhanced bootstrap --------------------------------
		let adjusted_util = if self.vr_ready {
			// We need to capture action_baseline for use outside the closure
			let mut action_baseline_value = 0.0;

			self.info_states()
				.with_row(opponent_key, num_actions, |row| {
					// --- keep baselines up-to-date for unbiased VR estimator ---
					if check_is_vr(&self.config) {
						if check_is_vr_ema(&self.config) {
							row.update_baseline_ema(child_util); // Update with EMA
							row.update_action_baseline_ema(sampled_idx as usize, child_util); // Update action baseline with EMA
						} else if check_is_vr_mean(&self.config) {
							row.update_baseline_mean(child_util);
							row.update_action_baseline_mean(sampled_idx as usize, child_util);
						}

						// Capture the action baseline value for use after the closure
						action_baseline_value =
							row.baseline_action_values[sampled_idx as usize].get(); // B(I,a)
					}
				});

			if check_is_vr(&self.config) {
				// External-sampling ξ = sampled_prob
				action_baseline_value + (child_util - action_baseline_value) / sampled_prob
			} else {
				child_util
			}
		} else {
			child_util
		};

		// Removed instrumentation: log_opponent_node_adjusted_return

		// value going into VR formula or returned directly
		let value_of_sampled_branch = child_util;

		if check_is_vr(&self.config) {
			// Update baselines if VR is enabled, regardless of warmup state
			self.info_states()
				.with_row(opponent_key, num_actions, |row| {
					// Note: If opponent_key was already seen due to vr_ready=true, this insert will do nothing.
					// If vr_ready=false but check_is_vr=true, this will correctly count it if new.
					row.update_baseline_ema(value_of_sampled_branch);
					row.update_action_baseline_ema(sampled_idx as usize, value_of_sampled_branch);
				});
		}

		adjusted_util
	}

	fn handle_opponent_node(
		&mut self,
		depth: usize,
		num_actions: usize,
		state: &mut G::State,
		player_to_update: PlayerId,
		reach_probabilities: &mut [Prob],
		current_strategy: &[f64; MAX_GRID],
		log_opponent_sampling: bool, // <-- Add flag parameter
	) -> Utility {
		let current_player = state.current_player();
		let opponent_key = self.abstraction.key(state, current_player); // <-- Get opponent key

		// Removed instrumentation: log_opponent_node_entry
		{
			let sampled_idx = sample_action_index(
				opponent_key,
				num_actions,
				current_strategy,
				&self.rng_pool,
				log_opponent_sampling,
				self.config.exploration_rate,
			);
			let sampled_prob = current_strategy[sampled_idx as usize];

			// Removed instrumentation: log_opponent_action_sampling

			// Apply the sampled action to the state and handle any errors
			if self.apply_opponent_action(
				state,
				sampled_idx,
				sampled_prob,
				0.0, // Not used anymore - will remove from function signature later
				0.0, // Not used anymore - will remove from function signature later
			).is_err() {
				return 0.0;
			}

			// Update reach probability for the opponent who just acted
			let mut child_reaches = reach_probabilities.to_vec();
			child_reaches[current_player] *= sampled_prob;
			
			let child_util = self.escfr_recursive(
				state,
				player_to_update,
				&mut child_reaches,
				depth + 1,
				log_opponent_sampling, // <-- Pass flag down
			);
			// Removed instrumentation: log_opponent_node_child_return

			if let Err(e) = state.undo_last_action() {
				error!("undo_last_action failed after opponent node: {}", e);
			}

			// Calculate adjusted utility using the helper method
			

			self.compute_opponent_adjusted_utility(
				opponent_key,
				num_actions,
				sampled_idx,
				sampled_prob,
				child_util,
			)
		}
	}

	/// Applies a traverser action, recursively evaluates it, and undoes the action.
	/// Returns the calculated utility for the action.
	#[inline]
	fn apply_evaluate_and_undo_traverser_action(
		&mut self,
		state: &mut G::State,
		concrete_action: ConcreteAction,
		_a_idx: usize, // Prefixed as unused
		action_prob: f64,
		reach_probabilities: &mut [Prob],
		player_to_update: PlayerId,
		depth: usize,
		next_log_opponent_sampling: bool,
	) -> Utility {
		// Try to apply the action, return 0.0 on error
		if let Err(e) = state.apply_action(concrete_action) {
			error!(
				"Error applying traverser action {:?}: {}",
				concrete_action,
				e
			);
			return 0.0;
		}

		// Removed instrumentation: log_traverser_action_recurse

		// Update reach probability for the player who just acted
		let mut child_reaches = reach_probabilities.to_vec();
		
		// Debug logging
		if self.iter_count <= 5 {
			// trace!(
			// 	"Player action (apply_evaluate_undo) - Before: {:?}, action_prob: {:.6}, player: {}", 
			// 	reach_probabilities, action_prob, player_to_update
			// );
		}
		
		child_reaches[player_to_update] *= action_prob;
		
		// Debug logging
		if self.iter_count <= 5 {
			// trace!(
			// 	"Player action (apply_evaluate_undo) - After: {:?}", 
			// 	child_reaches
			// );
		}
		
		// Make the recursive call
		let utility = self.escfr_recursive(
			state,
			player_to_update,
			&mut child_reaches,
			depth + 1,
			next_log_opponent_sampling,
		);

		// Removed instrumentation: log_traverser_action_return

		// Undo the action, log error if it fails
		if let Err(e) = state.undo_last_action() {
			error!(
				"undo_last_action failed after traverser action: {}",
				e
			);
		}

		utility
	}

	/// Calculate which actions should be skipped due to RBP pruning
	fn calculate_skipped_actions(
		&self,
		infoset_key: InfosetHashKey,
		num_actions: usize,
	) -> Vec<bool> {
		let mut skipped = vec![false; num_actions];
		
		if let Some(rbp) = &self.rbp_manager {
			let current_iter = self.iter_count;
			let rbp_threshold = rbp.config.base_threshold;
			let max_regret_per_iter = self.game.max_utility() - self.game.min_utility();
			let min_iterations = rbp.config.min_iterations_before_pruning;
			
			self.info_states.with_row(infoset_key, num_actions, |row| {
				for a_idx in 0..num_actions {
					let revisit_at = row.revisit_at[a_idx].load(Ordering::Relaxed);
					
					// Case 1: Currently pruned and not time to revisit yet
					if revisit_at > 0 && current_iter < revisit_at {
						skipped[a_idx] = true;
						continue;
					}
					
					// Case 2: Was pruned and now time to revisit - ALWAYS unprune first
					if revisit_at > 0 {
						// Clear the pruning state
						row.revisit_at[a_idx].store(0, Ordering::Relaxed);
						self.info_states.record_unprune_event();
						// TODO: Pay-back bulk regret update here if implementing full algorithm
						// Note: We don't skip here - let it fall through to check if should re-prune
					}
					
					// Case 3: Check if should prune (or re-prune after unpruning)
					let regret = row.cumulative_regrets[a_idx].get();
					if regret < rbp_threshold && current_iter >= min_iterations {
						// Calculate pruning duration
						let iterations_needed = rbp.calculate_pruning_duration(regret, max_regret_per_iter);
						let prune_until = current_iter + iterations_needed;
						
						row.revisit_at[a_idx].store(prune_until, Ordering::Relaxed);
						skipped[a_idx] = true;
						
						// Record metrics
						self.info_states.record_prune_decision();
						self.info_states.record_action_pruned();
					}
				}
			});
		}
		
		return skipped;
	}

	fn handle_player_node(
		&mut self,
		infoset_key: InfosetHashKey,
		depth: usize,
		num_actions: usize,
		state: &mut G::State,
		player_to_update: PlayerId,
		reach_probabilities: &mut [Prob],
		current_strategy: &[f64; MAX_GRID],
		_log_opponent_sampling: bool, // <-- Add flag parameter (though not used directly here)
	) -> Utility {
		let debug_key = infoset_key.0 == 0x01d76d6c53a310b7;
		debug_assert!(
			(0..num_actions).all(|i| current_strategy[i].is_finite()),
			"Non-finite prob encountered in current_strategy!"
		);

		let current_player = state.current_player();
		let num_players = self.game.num_players();
		
		// Calculate opponent counterfactual reach - product of all players' reaches except current player
		let mut opp_cf_reach = 1.0;
		for i in 0..num_players {
			if i != current_player {
				opp_cf_reach *= reach_probabilities[i];
			}
		}
		// Also multiply by chance reach if present
		if reach_probabilities.len() > num_players {
			opp_cf_reach *= reach_probabilities[num_players];
		}

		// Removed instrumentation: check_instrumentation
		let (should_log_instrumented, next_log_opponent_sampling) = (false, false);

		let mut node_value = 0.0;
		let mut action_values = [0.0; MAX_GRID];

		let _first_action_logged = false; // Flag to log only the first action (prefixed and made immutable)

		// Removed instrumentation: log_player_node_pre_recursion block

		// Calculate which actions to skip due to RBP
		let skipped_actions = self.calculate_skipped_actions(infoset_key, num_actions);
		let legal_actions = state.legal_actions();

		if debug_key {
			// println!("\n[PLAYER NODE DEBUG] Starting action evaluation");
			// println!("  Opponent CF reach: {:.6}", opp_cf_reach);
			// println!("  Player {} reach: {:.6}", current_player, reach_probabilities[current_player]);
			// println!("  Traverser {} reach: {:.6}", player_to_update, reach_probabilities[player_to_update]);
		}

	// Iterate over all legal actions for the traverser
	for (a_idx, &concrete_action) in legal_actions.iter().enumerate() {
		// Skip pruned actions
		if skipped_actions[a_idx] {
			action_values[a_idx] = 0.0; // Ensure value is 0
			if debug_key {
				// println!("  Action {} ({}): SKIPPED (pruned)", a_idx, concrete_action.0);
			}
			continue;
		}

		let action_prob = current_strategy[a_idx];
		// CRITICAL: In ES-CFR, we must evaluate ALL actions to compute counterfactual values,
		// even those with zero probability. This is required for correct regret updates.
		let val = self.apply_evaluate_and_undo_traverser_action(
			state,
			concrete_action,
			a_idx,
			action_prob,
			reach_probabilities,
			player_to_update,
			depth,
			next_log_opponent_sampling,
		);
		action_values[a_idx] = val;
		node_value += action_prob * val;

		if debug_key {
			// println!("  Action {} ({}): prob={:.6}, value={:.6}, contrib={:.6}", 
			// 	a_idx, concrete_action.0, action_prob, val, action_prob * val);
		}
	}

	// Calculate num_actions from mask here
	let _num_actions = num_actions;
	
	if debug_key {
		// println!("\n  Node value: {:.6}", node_value);
		// println!("  Action values: {:?}", &action_values[..num_actions]);
	}
	
		// Extract iter_count before the closure to avoid borrowing self inside
		let iter_count = self.iter_count;
		// Track regret action updates locally and add to metrics after the closure
		let mut regret_action_updates = 0;
		
		// Clone skipped_actions to use inside the closure
		let skipped_actions_clone = skipped_actions.clone();
		// Capture debug flag for closure
		let debug_this = debug_key;

		// Consolidated single closure for all operations - reduces HashMap lookups
		let return_util = self.info_states()
			.with_row(infoset_key, num_actions, |row| {
				// Update denominator ONCE per infoset (not per action!)
				let iteration_t = iter_count.max(1); // Ensure t >= 1 for weighting
				let iteration_weight = if check_is_linear_weighting(&self.config) {
					iteration_t as f64
				} else {
					1.0
				};
				// Use the TRAVERSER's reach for average strategy updates (like reference implementation)
				let denom_increment = iteration_weight * reach_probabilities[player_to_update];
				row.add_reach_denominator(denom_increment);
				
				// --- Baseline Updates (from first closure) ---
				self.update_baselines_if_vr_enabled(row, node_value, &action_values, num_actions);

				// Store baseline values for regret calculation
				let state_baseline = row.baseline_value.get(); // B(I)

				// --- Regret and Strategy Updates (from second closure) ---
				for a_idx in 0..row.num_actions as usize {
					// Skip updates for pruned actions - CRITICAL FIX
					if skipped_actions_clone[a_idx] {
						continue;
					}

					let action_baseline = row.baseline_action_values[a_idx].get(); // B(I,a)

					// Compute immediate regret
					let immediate_regret = if self.vr_ready {
						// VR-MCCFR:  (v(I,a)-B(I,a)) − (v(I)-B(I))
						(action_values[a_idx] - action_baseline) - (node_value - state_baseline)
					} else {
						// Classic CFR:  v(I,a) − v(I)
						action_values[a_idx] - node_value
					};

					// CRITICAL FIX: Weight by opponent CF reach (to the ACTING player)
					// In ES-CFR, regret updates must be weighted by π_{-i}(h)
					let regret_delta = opp_cf_reach * immediate_regret;

					// Debug logging for regret updates
					if log::log_enabled!(log::Level::Debug) {
						let action_str = state.action_to_string(current_player, legal_actions[a_idx]);
						let regret_before = row.cumulative_regrets[a_idx].get();
						log::debug!(
							"\n╔══════════════════════════════════════════════════════════════════════╗"
						);
						log::debug!(
							"║ REGRET UPDATE - Infoset: {} Player: P{}",
							infoset_key.0, current_player
						);
						
						// Try to downcast to Leduc state for additional info
						if let Some(leduc_state) = state.as_any().downcast_ref::<games::leduc::LeducState>() {
							log::debug!(
								"╠══════════════════════════════════════════════════════════════════════╣"
							);
							log::debug!(
								"║ GAME STATE:"
							);
							
							// Format cards properly
							let p0_card = leduc_state.hole_cards[0]
								.map(|c| c.to_string())
								.unwrap_or_else(|| "--".to_string());
							let p1_card = leduc_state.hole_cards[1]
								.map(|c| c.to_string())
								.unwrap_or_else(|| "--".to_string());
							let comm_card = leduc_state.community_card
								.map(|c| c.to_string())
								.unwrap_or_else(|| "--".to_string());
							
							log::debug!(
								"║   P0 hole: {} | P1 hole: {} | Community: {}",
								p0_card, p1_card, comm_card
							);
							log::debug!(
								"║   Round: {} | Pot: {} | Stakes: {}",
								leduc_state.round, leduc_state.pot, leduc_state.stakes
							);
							
							// Format betting history
							let history: Vec<String> = leduc_state.action_history.iter()
								.map(|(p, a)| {
									if *p == engine::types::CHANCE_PLAYER_ID as usize {
										"Deal".to_string()
									} else {
										format!("P{}:{}", p, match a.0 {
											0 => "F",
											1 => "C",
											2 => "R",
											_ => "?"
										})
									}
								})
								.collect();
							log::debug!(
								"║   History: {}",
								if history.is_empty() { "None".to_string() } else { history.join(" ") }
							);
						}
						
						log::debug!(
							"╠══════════════════════════════════════════════════════════════════════╣"
						);
						log::debug!(
							"║ Action: {} ({}) | ConcreteAction({})",
							a_idx, action_str, legal_actions[a_idx].0
						);
						log::debug!(
							"║ Strategy: {:.4} | Iteration: {}",
							current_strategy[a_idx], iter_count
						);
						log::debug!(
							"╠══════════════════════════════════════════════════════════════════════╣"
						);
						log::debug!(
							"║ Action Utility: {:.6} | Node Value: {:.6}",
							action_values[a_idx], node_value
						);
						log::debug!(
							"║ Immediate Regret: {:.6} (action_util - node_value)",
							immediate_regret
						);
						log::debug!(
							"║ Opponent CF Reach: {:.6} | Player Reach: {:.6}",
							opp_cf_reach, reach_probabilities[current_player]
						);
						log::debug!(
							"║ Regret Delta: {:.6} (opp_reach * immediate_regret)",
							regret_delta
						);
						log::debug!(
							"╠══════════════════════════════════════════════════════════════════════╣"
						);
						log::debug!(
							"║ Regret Before: {:.6}",
							regret_before
						);
						log::debug!(
							"║ Regret After:  {:.6}",
							regret_before + regret_delta
						);
						log::debug!(
							"╚══════════════════════════════════════════════════════════════════════╝"
						);
					}

					// Use appropriate regret update method based on configuration
					match self.config.regret_matching_mode {
						engine::solver_config::RegretMatchingMode::Standard => {
							row.add_regret(a_idx, regret_delta);
						}
						engine::solver_config::RegretMatchingMode::Plus => {
							row.add_regret_plus(a_idx, regret_delta);
						}
					}
					regret_action_updates += 1;
					
					if debug_this {
						// println!("  Regret update for action {}: immediate={:.6}, delta={:.6} (opp_cf_reach={:.6})",
						// 	a_idx, immediate_regret, regret_delta, opp_cf_reach);
					}
					// Use the TRAVERSER's reach (like reference implementation)
					let player_reach = reach_probabilities[player_to_update];
					
					self.update_average_strategy(
						row,
						a_idx,
						player_reach,
						current_strategy[a_idx],
						iter_count,
						should_log_instrumented,
					);
					
					if debug_this {
						// println!("  Avg strategy update for action {}: player_reach={:.6}, sigma={:.6}, weight={:.6}",
						// 	a_idx, player_reach, current_strategy[a_idx], 
						// 	(if check_is_linear_weighting(&self.config) { iter_count as f64 } else { 1.0 }) * player_reach * current_strategy[a_idx]);
					}
				}

				row.update_iteration(iter_count);
				
				if debug_this {
					// println!("\n  Final row state:");
					// println!("    Cumulative regrets: {:?}", &row.cumulative_regrets[..num_actions]);
					// println!("    Denominator: {:.6}", row.cumulative_reach_denominator_sum.get());
				}

				// --- Return Utility Calculation (from third closure) ---
				if self.vr_ready {
					let sum_action_baselines: f64 = (0..row.num_actions as usize)
						.map(|i| {
							current_strategy[i] * row.baseline_action_values[i].get()
						})
						.sum();
					row.baseline_value.get() + (node_value - sum_action_baselines)
				} else {
					node_value
				}
			});

		// Update metrics after the closure
		self.info_states.increment_regret_updates(regret_action_updates as u64);

		// Removed instrumentation: log_player_node_final_return
		// panic!("Forcing hard stop");
		return_util
	}

	/// Helper method to update regrets based on DCFR or vanilla/LCFR path.

	/// Helper method to update state and action baselines if variance reduction is enabled.
	#[inline]
	fn update_baselines_if_vr_enabled(
		&self,
		row: &regretmap::Row,
		node_value: Utility,
		action_values: &[f64; MAX_GRID],
		_num_actions: usize,
	) {
		if check_is_vr(&self.config) {
			// Update baselines if VR is enabled, regardless of warmup state
			if check_is_vr_ema(&self.config) {
				// 1) update the state baseline B(I) with EMA
				row.update_baseline_ema(node_value);

				// 2) update per-action baselines B(I,a) with EMA
				for (i, &action_val) in action_values.iter().enumerate().take(row.num_actions as usize) {
					row.update_action_baseline_ema(i, action_val);
				}
			} else if check_is_vr_mean(&self.config) {
				// 1) update the state baseline B(I) with EMA
				row.update_baseline_mean(node_value);

				// 2) update per-action baselines B(I,a) with EMA
				for (i, &action_val) in action_values.iter().enumerate().take(row.num_actions as usize) {
					row.update_action_baseline_mean(i, action_val);
				}
			}
		}
	}
	/// Helper method to update average strategy numerators and denominators.
	#[inline]
	fn update_average_strategy(
		&self,
		row: &regretmap::Row,
		a_idx: usize,
		player_reach: Prob,
		current_strategy_prob_for_action: Prob,
		iter_count: u64, // Changed to u64
		_should_log_instrumented: bool,
	) {
		let iteration_t = iter_count.max(1); // Ensure t >= 1 for weighting

		// For Vanilla/LCFR, calculate the iteration weight.
		let iteration_weight = if check_is_linear_weighting(&self.config) {
			iteration_t as f64
		} else {
			1.0
		}; // Use the helper method
		let strat_increment = iteration_weight * player_reach * current_strategy_prob_for_action;

		row.add_strategy_numerator(a_idx, strat_increment);
		// NOTE: We already updated the denominator once per infoset in handle_player_node,
		// so we don't update it here per action anymore

		// Removed instrumentation: log_avg_strat_update_details
	}

	/// Enable detailed logging for a specific infoset key every `freq` times it's encountered.
	/// (Instrumentation removed for performance)
	pub fn instrument_key(&mut self, _key_to_instrument: InfosetHashKey, _freq: usize) {
		// Instrumentation removed
	}

	/// Prints a report summarizing the observed opponent action sampling distributions.
	/// (Instrumentation removed for performance)
	pub fn print_opponent_sampling_report(&self) {
		// Instrumentation removed
	}

	// --- End Instrumentation Logging Helpers ---
} // end impl ExternalSamplingCfr

```

crates/algorithms/src/infostate_hook.rs:
```
use engine::types::{ConcreteAction, InfosetHashKey, PlayerId};
use std::any::Any;

/// Hook interface for capturing infostate information during ES-CFRF traversal.
/// This is used for debugging and analysis purposes.
pub trait InfostateHook: Send + Sync {
    /// Called when an infostate is visited during ES-CFRF traversal.
    ///
    /// # Arguments
    /// * `key` - The hash key identifying this infostate
    /// * `game_state` - Current game state (as Any for downcasting to specific game type)
    /// * `player` - Player whose perspective this infostate represents
    /// * `actions` - Legal concrete actions available at this infostate
    /// * `policy` - Probability distribution over actions
    fn on_infostate(
        &self,
        key: InfosetHashKey,
        game_state: &dyn Any,
        player: PlayerId,
        actions: &[ConcreteAction],
        policy: &[f64],
    );
}
```

crates/algorithms/src/lib.rs:
```
/* src/lib.rs */
#![allow(missing_docs)] // Suppress missing docs warnings
#![allow(clippy::empty_line_after_doc_comments)] // Suppress empty line after doc comment warnings
#![allow(clippy::too_many_arguments)] // Suppress warnings for functions with many arguments
#![deny(unsafe_code)] // <-- CHANGE forbid to deny

pub use crate::external_sampling_cfr::ExternalSamplingCfr;

// ── Public solver exports ────────────────────────────────────────────────
pub use crate::chance_sampling_cfr::ChanceSamplingCfr; // NEW: chance-sampling CFR
pub use crate::vanilla_cfr::VanillaCfr; // Full-tree CFR
pub use engine::solver_config::{DiscountMode, EpochMethod, SolverConfig}; // <-- CORRECTED PATH

// pub mod simulation;      // +++ Add simulation module +++ // Removed - file not found
pub mod xor_abstraction;

// --- Solver modules ---
pub mod chance_sampling_cfr;
pub mod es_factory; // ES-MCCFR Constructors
pub mod es_instrumentation; // ES-MCCFR instrumentation helpers
pub mod es_solver; // ES-MCCFR Solver trait implementations
pub mod external_sampling_cfr; // ES-MCCFR – opponent sampling
pub mod vanilla_cfr; // Full-tree CFR // NEW: chance-sampling CFR

// --- Utility Modules ---
// es_instrumentation moved up to be public
pub mod es_util; // Shared utilities for External Sampling variants
mod metrics; // Optional metrics collection
pub mod util; // Common utilities for all algorithms

// --- RBP Module ---
pub mod rbp; // Regret-Based Pruning implementation

// --- Search Module ---
pub mod depth_limited_solver; // Depth-limited search solver
pub mod search_policy; // Policy wrapper with search capability

// --- Hook Interface ---
pub mod infostate_hook; // Hook for capturing infostate information
pub use infostate_hook::InfostateHook;

```

crates/algorithms/src/metrics.rs:
```
/* src/metrics.rs */
#![allow(missing_docs)] // <-- ADD this line to suppress doc warnings globally for this crate

// atomic types used in metrics macros; fully-qualified paths used below

#[cfg(feature = "metrics")]
macro_rules! def {
	($n:ident) => {
		pub static $n: ::std::sync::atomic::AtomicU64 = ::std::sync::atomic::AtomicU64::new(0);
	};
}
#[cfg(not(feature = "metrics"))]
macro_rules! def {
	($n:ident) => {};
}

def!(ITERS); // ∑ run_iteration calls
def!(ROW_INSERTS); // successful writes of a new Row

/*
#[inline] pub fn dump_csv(path: Option<&str>) {
	#[cfg(feature="metrics")] {
		use std::{fs::File, io::{Write, BufWriter}, sync::atomic::Ordering};
		let write_metrics = |mut writer: Box<dyn Write>| -> std::io::Result<()> {
			writeln!(writer, "metric,value")?;
			macro_rules! w {($m:ident)=>{writeln!(writer, "{},{}", stringify!($m).to_lowercase(), $m.load(Ordering::Relaxed))?;};}
			w!(ITERS); w!(ROW_INSERTS);
			// Add other metrics here if defined
			Ok(())
		};
		let result = match path {
			Some(p) => {
				match File::create(p) {
					Ok(f) => write_metrics(Box::new(BufWriter::new(f))),
					Err(e) => {
						eprintln!("Error creating metrics file '{}': {}", p, e);
						write_metrics(Box::new(std::io::stdout()))
					}
				}
			}
			None => {
				write_metrics(Box::new(std::io::stdout()))
			}
		};
		if let Err(e) = result {
			 eprintln!("Error writing metrics: {}", e);
		}
	}
	#[cfg(not(feature="metrics"))] {
		let _ = path;
	}
}
*/

#[macro_export]
macro_rules! inc_metric {
	($ctr:ident,$d:expr) => {
		#[cfg(feature = "metrics")]
		{
			$crate::metrics::$ctr.fetch_add($d as u64, ::std::sync::atomic::Ordering::Relaxed);
		}
	};
}

```

crates/algorithms/src/rbp.rs:
```
//! Regret-Based Pruning (RBP) implementation for CFR algorithms
//! 
//! This implements Interval RBP as described in Brown & Sandholm (NIPS 2015).
//! Actions with negative cumulative regret are temporarily pruned to improve
//! performance without affecting convergence guarantees.
//!
//! IMPORTANT: RBP pruning is completely orthogonal to legal actions!
//! - Legal actions: Which moves are allowed by game rules
//! - Pruned actions: Which legal actions RBP temporarily ignores due to negative regret
//! 
//! With the Hybrid Lazy Approach:
//! - RBPManager only holds configuration (thresholds, check frequency)
//! - Row holds the actual pruning state (revisit_at, pruning_revision)
//! - No HashMap lookups needed, all operations are O(1) atomics
//!
//! See RBP_DESIGN.md for detailed design decisions.

use engine::types::InfosetHashKey;
use regretmap::InfoStatesMap;
use std::sync::Arc;

/// Configuration for Regret-Based Pruning
#[derive(Debug, Clone)]
pub struct PruningConfig {
    /// Base threshold for pruning (e.g., -0.001)
    pub base_threshold: f64,
    /// Whether to use dynamic thresholding
    pub use_dynamic_threshold: bool,
    /// Scaling factor for dynamic threshold (C in papers, default 300 from Libratus)
    pub dynamic_scaling_factor: f64,
    /// Maximum iterations to prune an action
    pub max_pruning_iterations: u64,
    /// Minimum number of iterations before pruning can start
    pub min_iterations_before_pruning: u64,
}

/// Manager for Regret-Based Pruning operations
/// 
/// With the Hybrid Lazy Approach, this only manages configuration.
/// All pruning state is stored directly in Row for efficiency.
pub struct RBPManager {
    pub config: PruningConfig,
    info_states: Arc<InfoStatesMap>,
}

impl RBPManager {
    /// Create a new RBP manager with the given configuration
    pub fn new(config: PruningConfig, info_states: Arc<InfoStatesMap>) -> Self {
        Self {
            config,
            info_states,
        }
    }

    /// Get debug statistics as a formatted string
    pub fn get_debug_stats(&self) -> String {
        format!(
            "RBP Stats: {} pruned actions, {} total decisions, {} unpruning events",
            self.info_states.rbp_actions_pruned(),
            self.info_states.rbp_prune_decisions(),
            self.info_states.rbp_unprune_events(),
        )
    }

    /// Determine if an action should be pruned based on cumulative regret
    /// 
    /// This is now just a helper that checks the threshold.
    /// The actual pruning logic is in ExternalSamplingCfr::should_skip_action()
    pub fn should_prune(
        &self,
        _infoset_key: InfosetHashKey,
        _action: u8,
        cumulative_regret: f64,
        current_iteration: u64,
        _total_infosets: usize,
    ) -> bool {
        // Don't prune if we haven't reached the minimum iterations
        if current_iteration < self.config.min_iterations_before_pruning {
            return false;
        }

        let threshold = self.get_pruning_threshold(current_iteration);
        cumulative_regret < threshold
    }

    /// Calculate threshold based on configuration
    pub fn get_pruning_threshold(&self, iteration: u64) -> f64 {
        if self.config.use_dynamic_threshold {
            // Dynamic threshold: -C / sqrt(T) as per Brown, Kroer & Sandholm 2017
            -self.config.dynamic_scaling_factor / (iteration as f64).sqrt()
        } else {
            self.config.base_threshold
        }
    }

    /// Calculate iterations until regret could become positive
    pub fn calculate_pruning_duration(
        &self,
        cumulative_regret: f64,
        max_regret_per_iteration: f64,
    ) -> u64 {
        if max_regret_per_iteration <= 0.0 {
            return self.config.max_pruning_iterations;
        }
        
        let iterations_needed = (-cumulative_regret / max_regret_per_iteration).ceil() as u64;
        iterations_needed.min(self.config.max_pruning_iterations)
    }

    /// Get pruning statistics
    pub fn get_stats(&self) -> PruningStats {
        PruningStats {
            temporarily_pruned_actions: self.info_states.rbp_actions_pruned() as usize,
            total_prune_decisions: self.info_states.rbp_prune_decisions() as usize,
            total_unprune_events: self.info_states.rbp_unprune_events() as usize,
            pruned_infosets: 0,  // No longer tracked in HashMap
        }
    }
}

/// Statistics about current pruning state
#[derive(Debug, Default)]
pub struct PruningStats {
    pub temporarily_pruned_actions: usize,
    pub total_prune_decisions: usize,
    pub total_unprune_events: usize,
    pub pruned_infosets: usize,
}
```

crates/algorithms/src/search_policy.rs:
```
use std::sync::{Arc, Mutex};
use std::sync::atomic::{AtomicU64, Ordering};
use engine::game::Game;
use engine::policy::{Policy, TabularPolicy, PackedPolicy};
use engine::error::GameResult;
use engine::types::InfosetHashKey;
use crate::depth_limited_solver::DepthLimitedSolver;

/// A policy that ALWAYS uses depth-limited search
pub struct SearchPolicy<G: Game> {
    blueprint: Arc<TabularPolicy<G>>,
    solver: Mutex<DepthLimitedSolver<G>>,
    searches_triggered: AtomicU64,
}

impl<G: Game> SearchPolicy<G> {
    pub fn new(
        blueprint: Arc<TabularPolicy<G>>,
        solver: DepthLimitedSolver<G>,
    ) -> Self {
        Self {
            blueprint,
            solver: Mutex::new(solver),
            searches_triggered: AtomicU64::new(0),
        }
    }
    
    pub fn searches_triggered(&self) -> u64 {
        self.searches_triggered.load(Ordering::Relaxed)
    }
}

impl<G: Game> Policy<G> for SearchPolicy<G> {
    fn get_state_policy(&self, state: &G::State) -> GameResult<PackedPolicy> {
        // ALWAYS trigger search - no conditions
        let search_count = self.searches_triggered.fetch_add(1, Ordering::Relaxed) + 1;
        log::info!("Triggering depth-limited search #{}", search_count);
        
        // Solve subgame (solver is already &mut through Mutex)
        match self.solver.lock().unwrap().solve_subgame(state) {
            Ok(result) => {
                log::info!("Search #{} completed successfully", search_count);
                // Get policy for current state from the solved subgame
                result.policy.get_state_policy(state)
            }
            Err(e) => {
                log::warn!("Search #{} failed, falling back to blueprint: {}", search_count, e);
                self.blueprint.get_state_policy(state)
            }
        }
    }
    
    fn get_state_policy_by_key(&self, _info_state_key: InfosetHashKey) -> GameResult<PackedPolicy> {
        // For key-based lookup, we need to force the tester to call get_state_policy
        // where we can actually run search. Return an error to trigger fallback.
        Err(engine::error::GameError::LogicError(
            "SearchPolicy requires full state information - use get_state_policy instead".to_string()
        ))
    }
    
    fn as_any(&self) -> &dyn std::any::Any {
        self
    }
    
    fn as_any_mut(&mut self) -> &mut dyn std::any::Any {
        self
    }
}
```

crates/algorithms/src/util.rs:
```
//! Common utilities for algorithms

use engine::types::ConcreteAction;


/// Get the concrete action at a given index in the legal actions array.
/// 
/// This is trivial with direct indexing - just return the action at that position.
#[inline]
pub fn index_to_concrete_action(legal_actions: &[ConcreteAction], idx: usize) -> ConcreteAction {
    legal_actions[idx]
}
```

crates/algorithms/src/vanilla_cfr.rs:
```
use engine::abstraction::InformationAbstraction;
use engine::game::Game;
use crate::util::index_to_concrete_action;
use engine::policy::PackedPolicy; // <-- ADD THIS LINE
use engine::policy::TabularPolicy;
use engine::solver::Solver;
use engine::state::State;
use engine::types::{
	InfosetHashKey, PlayerId, Prob, Utility, MAX_GRID,
};
   // use itertools::Itertools; // <-- Remove this line
   // Removed unused format_f64_slice, format_policy
use cfr_rng::CfrRngPool; // Import CfrRngPool
use log::{error, warn}; // <-- Import warn macro, REMOVED trace
use regretmap::InfoStatesMap;
// Removed ScratchRow, LocalShardedTable imports
use crate::es_instrumentation; // <-- ADD THIS LINE
use crate::inc_metric; // <-- Add this line
use engine::solver::PlayerAwareSolver;
// Removed unused ScratchBuffers import
use std::sync::Arc;
// use std::sync::atomic::{AtomicBool, Ordering}; // Use AtomicBool for thread safety
use engine::solver_config::SolverConfig; // <-- CHANGE THIS LINE

/// Vanilla CFR Solver (Full Tree Traversal) - Single-threaded
pub struct VanillaCfr<G: Game> {
	game: Arc<G>,
	abstraction: Arc<dyn InformationAbstraction<G>>,
	info_states: Arc<InfoStatesMap>,
	_config: SolverConfig,  // <-- Prefix with underscore
}

// Removed new() constructor - use with_abstraction() to explicitly pass information abstraction

impl<G> VanillaCfr<G>
where
	G: Game,
	G::State: State<Game = G> + 'static,
{
	pub fn with_abstraction(
		game: Arc<G>,
		abstraction: Arc<dyn InformationAbstraction<G>>,
		info_states: Arc<InfoStatesMap>,
		_config: SolverConfig, // <-- Prefix with underscore
	) -> Self {
		Self {
			game,
			abstraction,
			info_states,
			_config,                           // <-- Use prefixed name
		}
	}

	/// Access to the underlying ShardedTable (returns a reference).
	pub fn info_states(&self) -> &InfoStatesMap {
		// Derefs Arc<InfoStatesMap> to &InfoStatesMap
		&self.info_states
	}

	/// Executes one *outer* iteration where each player is traversed exactly
	/// once.  This is a convenience wrapper for small diagnostic binaries –
	/// Prints a table summarizing
	// Removed run_one_iteration helper method as it used rand::thread_rng

	/// Perform one traversal of Vanilla CFR for a specific player.
	/// This is the core logic called by run_iteration_for_player.
	fn run_one_traversal(&mut self, player_to_update: PlayerId, rng_pool: &mut CfrRngPool) {
		inc_metric!(ITERS, 1);
		let mut initial_state = self.game.new_initial_state(rng_pool);
		let num_players = self.game.num_players(); // Get num_players
											 // Allocate the mutable reach probs vector directly
		let mut initial_reach_probs_mut = vec![1.0; num_players + 1]; // Size N+1 for players + chance

		// Allocate buffers once per traversal
		let mut utils_buffer = vec![0.0; num_players];
		let mut child_utils_buffer = vec![0.0; num_players]; // Allocate child buffer here
													   // let mut action_utils_flat_buffer = vec![0.0; MAX_GRID * num_players]; // +++ Allocate flat buffer here +++ // <-- Removed unused variable
													   // grandchild and deeper buffers will be allocated inside recursive calls
													   // Pass the directly allocated mutable vector
		self.vanilla_cfr_recursive(
			&mut initial_state,
			&mut initial_reach_probs_mut, // Pass mutable slice directly
			player_to_update,
			&mut utils_buffer,       // Pass mutable slice for parent utils
			&mut child_utils_buffer, // Pass mutable slice for child utils
		);
	} // <-- Removed unused variable warning by removing the variable itself

	// apply_regret_matching function removed entirely.

	// apply_regret_matching function removed entirely.

	/// Recursive Vanilla CFR traversal function.
	/// Calculates utility vector for the state for all players and writes it to `utils_out`.
	/// Updates regrets and average strategy components for the acting player at this node.
	fn vanilla_cfr_recursive(
		&mut self,
		state: &mut G::State,
		reach_probs: &mut [Prob],           // Pass mutable slice
		update_player: PlayerId,            // Which player's values are being updated in this traversal
		utils_out: &mut [Utility],          // Output slice for utilities
		child_utils_buffer: &mut [Utility], // Buffer for recursive calls
	) {
		// Returns nothing
		let current_player = (*state).current_player();
		let num_players = self.game.num_players();
		debug_assert_eq!(utils_out.len(), num_players, "utils_out length mismatch");
		// grandchild_utils_buffer is now passed in

		// --- 1. Base Cases ---
		if (*state).is_terminal() {
			let returns = (*state).returns();
			debug_assert_eq!(
				returns.len(),
				num_players,
				"Terminal returns length mismatch"
			);
			// Write returns to output slice
			utils_out.copy_from_slice(&returns);
			return;
		}

		if (*state).is_chance_node() {
			// Pass only required buffers to chance handler
			self.handle_vanilla_chance_node(
				state,
				reach_probs,
				update_player,
				utils_out,
				child_utils_buffer,
			); // +++ Pass flat buffer +++
			return;
		}

		// --- Player Node Logic ---
		let key = self.abstraction.key(&*state, current_player);

		let legal_actions = state.legal_actions();
		let num_actions = legal_actions.len();

		// ---------- phase 1: obtain data -------------------------------
		let current_strategy_sigma_t = {
			self.info_states.with_row(key, num_actions, |row| {
				let mut s = [0.0; MAX_GRID];
				row.write_current_strategy_into(row.num_actions as usize, &mut s);
				s
			})
		};

		// b) After a full tree traversal Σ_a σ(I,a) ≃ 1 (on the stack array!)
		let sum_sigma: f64 = (0..num_actions)
			.map(|i| current_strategy_sigma_t[i])
			.sum();
		debug_assert!(
			(sum_sigma - 1.0).abs() < 1e-9,
			"σ(I) not normalised: sum={:.12} at key {:?} num_actions {}",
			sum_sigma,
			key,
			num_actions
		);

		if num_actions == 0 {
			error!(
				"No actions available at non-terminal state {}",
				(*state).to_string()
			);
			// Write zeros to output slice
			utils_out.fill(0.0);
			return;
		}

		// Allocate temporary storage for action utilities.
		// Use a fixed-size array on the stack for node_utility_vec.
		let mut node_utility_vec = [0.0; 16]; // Assume max 16 players for stack allocation
		let node_utility_slice = &mut node_utility_vec[..num_players];
		// Allocate the flat buffer for action utilities needed by handle_action_recurse.
		// This buffer will be filled by the recursive calls.
		// Use a stack-allocated array if MAX_GRID * num_players is reasonably small,
		// otherwise keep the Vec allocation. Let's assume it might be large and keep Vec for now.
		// If MAX_GRID is small (e.g., <= 32) and num_players <= 16, stack allocation is feasible.
		// Example stack allocation (adjust size as needed):
		// const MAX_FLAT_UTILS: usize = MAX_GRID * 16; // Example max size
		// let mut action_utils_flat_buffer_arr = [0.0; MAX_FLAT_UTILS];
		// let mut action_utils_flat_buffer = &mut action_utils_flat_buffer_arr[..MAX_GRID * num_players];
		// For now, keep Vec but make it mutable only if needed by handle_update_strategy
		let mut action_utils_flat_buffer = vec![0.0; MAX_GRID * num_players]; // Size MAX_GRID * N

		self.handle_action_recurse(
			state,
			current_player,
			reach_probs, // Pass mutable slice down
			num_actions,
			&current_strategy_sigma_t,
			update_player,
			node_utility_slice,            // Pass mutable slice for node utilities (Output)
			&mut action_utils_flat_buffer, // Pass the allocated buffer (Output)
			child_utils_buffer,            // Pass down child buffer (used for grandchild output)
		);

		// --- compute reach probabilities needed for updates ---
		let player_reach_prob = reach_probs[current_player];
		let opp_reach_prob = reach_probs
			.iter()
			.enumerate()
			.filter(|(idx, _)| *idx != current_player)
			.fold(1.0, |acc, (_, p)| acc * *p);

		// Pass the filled action_utils_flat_buffer to handle_update_strategy.
		self.handle_update_strategy(
			key,
			current_player,
			num_actions,
			node_utility_slice,
			&action_utils_flat_buffer,
			player_reach_prob,
			opp_reach_prob,
			&current_strategy_sigma_t,
			update_player,
		);

		// Write the final node utility to the output slice
		utils_out.copy_from_slice(node_utility_slice);
	}

	fn handle_action_recurse(
		&mut self,
		state: &mut G::State,
		current_player: PlayerId,
		reach_probs: &mut [Prob], // Pass mutable slice
		_num_actions: usize,
		strategy_sigma: &[f64; MAX_GRID],
		update_player: PlayerId,
		node_utility_out: &mut [Utility],      // Size N (Output)
		action_utils_flat_out: &mut [Utility], // Size MAX_GRID * N (Output) - RENAMED
		child_utils_buffer: &mut [Utility],    // Size N (Used for grandchild output) - REPURPOSED
	) {
		// Returns nothing
		let num_players = self.game.num_players();
		debug_assert_eq!(node_utility_out.len(), num_players);
		// Assert argument buffer sizes
		debug_assert_eq!(action_utils_flat_out.len(), MAX_GRID * num_players);
		debug_assert_eq!(child_utils_buffer.len(), num_players);

		// Zero out the output slices initially
		node_utility_out.fill(0.0);
		action_utils_flat_out.fill(0.0); // +++ Zero the output flat slice buffer +++
								   // No need to zero action_utilities_out[idx] before writing below

		// Use the passed-down child_utils_buffer instead of allocating locally
		// let mut child_utils_buffer = vec![0.0; num_players]; // REMOVED // This comment is correct, no change needed here

		let legal_actions = state.legal_actions();
		for (idx, &action_prob) in strategy_sigma.iter().enumerate().take(legal_actions.len()) {
			// Use direct indexing
			let concrete = index_to_concrete_action(&state.legal_actions(), idx);
			#[cfg(debug_assertions)]
			{
				let ok = state.legal_actions().contains(&concrete);
				debug_assert!(
					ok,
					"VanillaCFR: Concrete action {:?} (from index {}) not legal in state:\n{}",
					concrete,
					idx,
					(*state).to_string()
				);
			}

			state.apply_action(concrete).expect("apply");
			// --- propagate player's action-probability down the tree ---
			let original_reach = reach_probs[current_player];
			reach_probs[current_player] *= action_prob;

			// Call recursive function, writing results into child_utils_buffer
			// Child writes its result into child_utils_buffer (passed in).
			// Child needs its *own* buffer to pass down to grandchildren.
			// Allocate the buffer on the stack.
			let mut grandchild_utils_buffer_arr = [0.0; 16]; // Stack allocation
			let grandchild_utils_buffer = &mut grandchild_utils_buffer_arr[..num_players]; // Slice for current num_players
			self.vanilla_cfr_recursive(
				state,
				reach_probs, // Pass modified mutable slice
				update_player,
				child_utils_buffer,      // Child writes its result here (Arg 5)
				grandchild_utils_buffer, // Child passes the stack-allocated slice down (Arg 6)
			);

			// Restore reach_probs after recursive call returns
			reach_probs[current_player] = original_reach;
			state.undo_last_action().expect("undo");

			// Copy results from buffer into the correct segment of the flat output slice
			let start = idx * num_players;
			let end = start + num_players;
			action_utils_flat_out[start..end].copy_from_slice(child_utils_buffer); // +++ Write to output flat buffer +++

			// Accumulate into node_utility_out
			for p in 0..num_players {
				node_utility_out[p] += strategy_sigma[idx] * child_utils_buffer[p];
				// weight by σ(I,a)
			}
		}

		// No return value needed
	}

	#[inline]
	fn handle_update_strategy(
		&mut self,
		key: InfosetHashKey,
		current_player: PlayerId,
		num_actions: usize,
		node_utility: &[Utility], // length = #players
		action_utils: &[Utility], // flat slice: MAX_GRID × #players
		player_reach: Prob,       // traverser reach πᵢ
		opp_reach: Prob,          // opponent reach π₋ᵢ
		sigma: &[f64; MAX_GRID],
		update_player: PlayerId,
	) {
		// --- always: D += πᵢ  and  S += πᵢ·σ  -------------------------------
		self.info_states.with_row(key, num_actions, |row| {
			// Instrumentation: Log row state BEFORE updates
			// For VanillaCFR, should_log_instrumented is effectively false, iter_count is 1, vr_ready is false.
			// es_instrumentation::log_row_state("BEFORE", row, key, state_mask, false, 1, false);

			let approx_denominator_sum_before_update = row.cumulative_reach_denominator_sum.get();
			// For VanillaCFR, linear_weighting is false. avg_strat_denominator_increment_for_visit is player_reach.
			es_instrumentation::log_avg_strat_header(
				key,
				opp_reach, // opp_cf_reach
				player_reach, // avg_strat_denominator_increment_for_visit
				false,     // should_log_instrumented
				1,         // iter_count
				false,     // linear_weighting
				approx_denominator_sum_before_update,
			);

			row.add_reach_denominator(player_reach);
			let pi_i = player_reach;
			for (idx, &sigma_val) in sigma.iter().enumerate().take(row.num_actions as usize) {
				let strat_increment = pi_i * sigma_val;
				row.add_strategy_numerator(idx, strat_increment);

				// Instrumentation: Log average strategy update details
				es_instrumentation::log_avg_strat_update_details(
					idx,
					sigma[idx],
					strat_increment,
					false, // should_log_instrumented
				);
			}

			if current_player != update_player {
				// Instrumentation: Log row state AFTER updates if returning early
				es_instrumentation::log_avg_strat_footer(key, false);
				// es_instrumentation::log_row_state("AFTER", row, key, state_mask, false, 1, false);
				return;
			}

			let num_players = self.game.num_players();
			let node_value_for_update_player = node_utility[current_player];

			for idx in 0..row.num_actions as usize {
				let flat_idx_for_action_util = idx * num_players + current_player;
				let u_action = action_utils[flat_idx_for_action_util];
				
				let regret_delta = opp_reach * (u_action - node_value_for_update_player);

				// Instrumentation: Log regret update details
				// For VanillaCFR, vr_ready is false. reference_value is node_value_for_update_player.
				// action_values for the specific action `idx` is `u_action`.
				// We need to pass a slice for action_values to log_regret_updates_and_check_validity.
				// However, the current `action_utils` is flat.
				// For simplicity in this step, we'll call the more granular `log_regret_update_details`.
				// A more complete alignment would require restructuring how action utilities are passed or logged.
				es_instrumentation::log_regret_update_details(
					key,
					idx,
					u_action, // action_value for this action
					node_value_for_update_player, // reference_value (node_value for current player)
					regret_delta,
					opp_reach, // opp_cf_reach
					false,     // should_log_instrumented
					false,     // vr_ready
				);
				if !regret_delta.is_finite() {
					error!(
						"NaN/Inf detected in VanillaCFR regret update for key {:?}, action_idx {:?} (regret_delta={:.2}). Skipping update.",
						key, idx, regret_delta
					);
				} else {
					row.add_regret(idx, regret_delta);
				}
			}

			// Instrumentation: Log average strategy footer and row state AFTER updates
			es_instrumentation::log_avg_strat_footer(key, false);
			// es_instrumentation::log_row_state("AFTER", row, key, state_mask, false, 1, false);
		});
	}

	/// Handles chance node logic for Vanilla CFR. Writes results to `utils_out`.
	fn handle_vanilla_chance_node(
		&mut self,
		state: &mut G::State,
		reach_probs: &mut [Prob], // Pass mutable slice
		update_player: PlayerId,
		utils_out: &mut [Utility],          // Output slice
		child_utils_buffer: &mut [Utility], // Buffer for recursive calls
	) {
		// Returns nothing
		let outcomes = state.chance_outcomes();
		let num_players = self.game.num_players();
		// Assert buffer sizes
		debug_assert_eq!(child_utils_buffer.len(), num_players);
		debug_assert_eq!(utils_out.len(), num_players);

		if outcomes.is_empty() {
			error!("Chance node {} has no outcomes!", (*state).to_string());
			utils_out.fill(0.0); // Write zeros to output
			return;
		}

		// Zero out the output slice initially
		utils_out.fill(0.0);
		// Use the passed-down child_utils_buffer instead of allocating locally
		// let mut child_utils_buffer = vec![0.0; num_players]; // REMOVED // This comment is correct, no change needed here

		for outcome in outcomes {
			let concrete = outcome.0;
			let chance_prob = outcome.1;
			state.apply_action(concrete).expect("apply chance");

			// Modify reach_probs in place (update chance probability at index num_players)
			let chance_index = num_players;
			let original_chance_reach = if chance_index < reach_probs.len() {
				let val = reach_probs[chance_index];
				reach_probs[chance_index] *= chance_prob;
				val // Store original value
			} else {
				warn!("Reach probs length ({}) doesn't include chance index ({}). Chance prob not applied to reach.", reach_probs.len(), chance_index);
				1.0 // Assume original was 1.0 if index is missing
			};

			// Let's assume reach_probs includes chance at index num_players.
			// If not, this needs adjustment. Assuming it does for now:
			// NOTE: The in-place modification logic already handles this check.
			// This block seems redundant now. We can remove it or keep the warning.
			// Let's keep the warning logic but use reach_probs.
			if num_players >= reach_probs.len() {
				// This case implies reach_probs didn't include chance.
				// The interpretation of reach_probs needs clarification.
				// For now, let's proceed without modifying reach if chance isn't included.
				// warn! is already called inside the in-place modification logic if index is out of bounds.
				// This specific warning location is now redundant.
			}
			// The actual multiplication happens within the in-place modification block above.

			// Child writes its result into child_utils_buffer (passed in).
			// Child needs its *own* buffer to pass down to grandchildren.
			// Allocate the buffer on the stack.
			let mut grandchild_utils_buffer_arr = [0.0; 16]; // Stack allocation
			let grandchild_utils_buffer = &mut grandchild_utils_buffer_arr[..num_players]; // Slice for current num_players
			self.vanilla_cfr_recursive(
				state,
				reach_probs, // Pass modified mutable slice
				update_player,
				child_utils_buffer,      // Child writes its result here (Arg 5)
				grandchild_utils_buffer, // Child passes the stack-allocated slice down (Arg 6)
			);

			// Restore chance reach probability
			if chance_index < reach_probs.len() {
				reach_probs[chance_index] = original_chance_reach;
			}

			// Accumulate weighted child utilities into utils_out
			// Child utilities already include chance probability because reach_probs[chance] was scaled
			for p in 0..num_players {
				utils_out[p] += chance_prob * child_utils_buffer[p]; // weight by outcome prob
			}

			state.undo_last_action().expect("undo chance");
		}
		// No return value needed
	}
}

// Implement Solver trait for VanillaCfr
impl<G> Solver<G> for VanillaCfr<G>
where
	G: Game,
	G::State: State<Game = G> + 'static,
{
	/// Runs one full iteration (one traversal for each player).
	/// Ignores the provided RNG pool as Vanilla CFR is deterministic.
	fn run_iteration(&mut self, rng_pool: &CfrRngPool) {
		// Use CfrRngPool, make mutable
		// Call run_iteration_for_player with None to trigger default behavior (all players)
		self.run_iteration_for_player(None, rng_pool); // Pass the pool
	}

	fn average_policy(&self) -> Arc<TabularPolicy<G>> {
		let mut policy = TabularPolicy::new(
			self.abstraction.clone() as Arc<dyn InformationAbstraction<G>>,
			true
		); // Enable uniform fallback
											 // Iterate over the ShardedTable (yields Arc<Row>)
		for (key, row_arc) in self.info_states.iter() {
			let values = &*row_arc; // Dereference Arc<Row> to &Row
			let avg_policy_for_key = values
				.get_average_policy(Some(key)) // Pass key by value
				.unwrap_or_else(|e| {
					error!("Error generating average policy for key {:?}: {}", key, e);
					PackedPolicy::new(0, &[])
				});
			policy.set_packed_policy(key, avg_policy_for_key); // <-- Remove &
		}
		Arc::new(policy)
	}

	fn current_policy(&self) -> Arc<TabularPolicy<G>> {
		let mut policy = TabularPolicy::new(
			self.abstraction.clone() as Arc<dyn InformationAbstraction<G>>,
			true
		); // Enable uniform fallback
											 // Iterate over the ShardedTable (yields Arc<Row>)
		for (key, row_arc) in self.info_states.iter() {
			let values = &*row_arc; // Dereference Arc<Row> to &Row
						   // get_current_policy calculates RM on the fly from atomic regrets.
			let current_policy_for_key = values.get_current_policy().unwrap_or_else(|e| {
				error!("Error generating current policy for key {:?}: {}", key, e);
				PackedPolicy::new(0, &[])
			});
			policy.set_packed_policy(key, current_policy_for_key); // <-- Remove &
		}
		Arc::new(policy)
	}

    fn num_info_states(&self) -> usize {
        self.info_states.iter().len()
    }


	// +++ Implement as_any and as_any_mut +++
	fn as_any(&self) -> &dyn std::any::Any {
		self
	}
	fn as_any_mut(&mut self) -> &mut dyn std::any::Any {
		self
	}

}

// Implement PlayerAwareSolver for VanillaCfr
impl<G> PlayerAwareSolver<G> for VanillaCfr<G>
where
	G: Game,
	G::State: State<Game = G> + 'static,
{
	/// Runs one iteration, updating only the specified `player`.
	/// If `player` is `None`, runs one traversal for *each* player sequentially.
	/// Ignores the provided RNG pool.
	fn run_iteration_for_player(&mut self, player: Option<PlayerId>, rng_pool: &CfrRngPool) {
		// Use CfrRngPool, make mutable
		let mut cloned_rng_pool = rng_pool.clone(); // Clone to get a mutable pool
		if let Some(p) = player {
			self.run_one_traversal(p, &mut cloned_rng_pool);
		} else {
			// Default behavior: run one traversal for each player
			for p in 0..self.game.num_players() {
				self.run_one_traversal(p as PlayerId, &mut cloned_rng_pool);
			}
		}
	}

	fn mark_iteration(&mut self, _global_iteration: u64) {
		// Vanilla CFR does not need to track iterations.
	}
}

// -------------------------------------------------------------------------
// Inherent methods only (not part of the PlayerAwareSolver trait)
// -------------------------------------------------------------------------


```

crates/algorithms/src/xor_abstraction.rs:
```
//! Tiny demo abstraction: XORs the raw infoset key with a fixed mask.
//! – bijective ⇒ still collision‑free, but changes the numeric space.

use engine::{
	abstraction::InformationAbstraction,
	game::Game,
	state::State,
	types::{InfosetHashKey, PlayerId},
};

#[derive(Clone, Debug)]
pub struct XorAbstraction {
	mask: u64,
}

impl Default for XorAbstraction {
	fn default() -> Self {
		Self {
			mask: 0x9E37_79B9_7F4A_7C15,
		} // any odd 64‑bit constant
	}
}

impl XorAbstraction {
	pub fn new(mask: u64) -> Self {
		Self { mask }
	}
}

impl<G: Game> InformationAbstraction<G> for XorAbstraction {
	#[inline]
	fn key(&self, state: &G::State, player: PlayerId) -> InfosetHashKey {
		let raw = state.information_state_key(player).0;
		InfosetHashKey(raw ^ self.mask)
	}
	fn id(&self) -> &'static str {
		"xor_mask"
	}
}

```

crates/trainers/src/base_trainer.rs:
```
use std::sync::Arc;

use cfr_rng::CfrRngPool; // Import the custom RNG pool

use regretmap::InfoStatesMap;

use engine::abstraction::InformationAbstraction;
use engine::game::Game;
use engine::solver::PlayerAwareSolver;
// Import SeatScheduler trait to access `next_player` method on scheduler types
// Import SeatScheduler trait for method resolution; alias as `_` to avoid unused_import warning
#[allow(unused_imports)]
use engine::scheduler::SeatScheduler as _;

// Conditional imports based on enabled features to avoid unused imports when features are disabled
#[cfg(any(feature = "parallel", feature = "single_threaded"))]
use engine::policy::TabularPolicy;

use engine::error::GameResult;

use engine::solver_config::SolverConfig;

#[cfg(feature = "parallel")]
use engine::scheduler::RoundRobin;

#[cfg(any(feature = "parallel", feature = "single_threaded"))]
use engine::trainer::Trainer;

use log::info;
#[cfg(feature = "parallel")]
use log::debug;

#[cfg(any(feature = "parallel", feature = "single_threaded"))]
use std::any::Any;

#[cfg(feature = "parallel")]
use std::time::Duration;

use engine::solver_config::EpochMethod;
use std::sync::atomic::{AtomicU64, Ordering as AtomicOrdering};

use std::marker::PhantomData; // ADDED
use engine::position::{RotationSchedule, PositionMapping};
use engine::position_context::set_position_context;

// --- Global iteration counter and epoch parameters ------------------------
// static TOTAL_ITERS: AtomicU64 = AtomicU64::new(0); // Removed global static

/// Generic *embarrassingly‑parallel* trainer that repeatedly calls
/// [`train_parallel`] until the requested wall‑clock time has elapsed.
///
/// supplies a `solver_factory` closure that instantiates the solver for each
/// worker thread.
#[allow(dead_code)]
pub struct BaseTrainer<G, F>
where
	G: Game + Send + Sync + 'static,
	G::State: engine::state::State<Game = G> + 'static,
	F: Fn(
			Arc<G>,
			Arc<InfoStatesMap>,
			&CfrRngPool,
			SolverConfig,
		) -> Box<dyn PlayerAwareSolver<G> + Send + 'static>
		+ Send
		+ Sync
		+ 'static,
{
	game: Arc<G>,
	num_threads: usize,
	solver_factory: std::sync::Arc<F>,
	solver_config: SolverConfig,
	rng_pool: CfrRngPool, // Add RNG pool field

	/// The single, shared, concurrently updated infoset table.
	infosets: Arc<InfoStatesMap>,
	/// Abstraction used for creating policies
	abstraction: Arc<dyn InformationAbstraction<G>>,
	/// Total iterations run by this trainer instance in its current `run` call.
	iterations: u64,
	/// Counter for total iterations, used for epoch and warmup logic.
	total_iterations_counter: Arc<AtomicU64>,
	/// Shared reference to the global epoch counter from the InfoStatesMap.
	global_epoch_counter: Arc<AtomicU64>,

	/// Rotation schedule for position fairness
	rotation_schedule: RotationSchedule,

	_game_marker: PhantomData<G>, // Keep PhantomData
}

// Manual `Debug` implementation because the factory closure may not be
// `Debug`.  We only print the fields that are always debuggable.
#[allow(clippy::missing_fields_in_debug)]
impl<G, F> std::fmt::Debug for BaseTrainer<G, F>
where
	G: Game + Send + Sync + 'static,
	G::State: engine::state::State<Game = G> + 'static,
	F: Fn(
			Arc<G>,
			Arc<InfoStatesMap>,
			&CfrRngPool,
			SolverConfig,
		) -> Box<dyn PlayerAwareSolver<G> + Send + 'static>
		+ Send
		+ Sync
		+ 'static,
{
	fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
		let mut debug_struct = f.debug_struct("BaseTrainer");
		debug_struct.field("num_threads", &self.num_threads);
		debug_struct.field("solver_config", &self.solver_config);
		debug_struct.field("rotation_schedule", &self.rotation_schedule);
		debug_struct.field("_game_marker", &self._game_marker); // Include marker if needed
		debug_struct.finish()
	}
}

impl<G, F> BaseTrainer<G, F>
where
	G: Game + Send + Sync + 'static,
	G::State: engine::state::State<Game = G> + 'static,
	F: Fn(
			Arc<G>,
			Arc<InfoStatesMap>,
			&CfrRngPool,
			SolverConfig,
		) -> Box<dyn PlayerAwareSolver<G> + Send + 'static>
		+ Send
		+ Sync
		+ 'static,
{
	/// Creates a new `BaseTrainer`.
	///
	/// * `game` – shared game description.
	/// * `num_threads` – size of the Rayon worker pool.
	/// * `solver_factory` – closure that constructs a boxed solver for the
	///   calling thread.
	/// * `infosets` – The shared information state map to use and update.
	/// * `abstraction` – The abstraction to use when creating policies.
	/// * `rng_pool` – The RNG pool to use for generating random numbers.
	#[cfg(all(feature = "parallel", not(feature = "single_threaded")))]
	pub fn new(
		game: Arc<G>,
		num_threads: usize,
		solver_config: SolverConfig,
		solver_factory: F,
		infosets: Arc<InfoStatesMap>,
		abstraction: Arc<dyn InformationAbstraction<G>>,
		rng_pool: CfrRngPool, // Add rng_pool parameter
	) -> Self {
		info!(
			"[BaseTrainer] Creating PARALLEL trainer with threads: {}, config: {:?}, RNG pool: {:?}",
			num_threads,
			solver_config,
			rng_pool
		);
		// Always create rotation schedule for proper position fairness
		let rotation_schedule = RotationSchedule::new(game.num_players());
		
		Self {
			game,
			num_threads,
			solver_factory: std::sync::Arc::new(solver_factory),
			solver_config,
			rng_pool, // Store the pool
			infosets: infosets.clone(),
			abstraction,
			iterations: 0,
			total_iterations_counter: Arc::new(AtomicU64::new(0)),
			global_epoch_counter: infosets.get_global_epoch_arc(),
			rotation_schedule,
			_game_marker: PhantomData,
		}
	}

	/// Creates a new `BaseTrainer` (Single-threaded or Both-Features version).
	#[cfg(all(feature = "single_threaded", not(feature = "parallel")))]
	pub fn new(
		game: Arc<G>,
		num_threads: usize, // Keep num_threads, even if it's 1 for single-threaded
		solver_config: SolverConfig,
		solver_factory: F,
		infosets: Arc<InfoStatesMap>,
		abstraction: Arc<dyn InformationAbstraction<G>>,
		rng_pool: CfrRngPool, // Add rng_pool parameter
	) -> Self {
		info!("[BaseTrainer] Creating SINGLE_THREADED trainer (or both features enabled) with config: {:?}, RNG pool: {:?}", solver_config, rng_pool);
		// Always create rotation schedule for proper position fairness
		let rotation_schedule = RotationSchedule::new(game.num_players());
		
		Self {
			game,
			num_threads,
			solver_factory: std::sync::Arc::new(solver_factory),
			solver_config,
			rng_pool, // Store the pool
			infosets: infosets.clone(),
			abstraction,
			iterations: 0,
			total_iterations_counter: Arc::new(AtomicU64::new(0)),
			global_epoch_counter: infosets.get_global_epoch_arc(),
			rotation_schedule,
			_game_marker: PhantomData,
		}
	}

	// Compile error if both features are enabled - this is not allowed.
	#[cfg(all(feature = "parallel", feature = "single_threaded"))]
	compile_error!("Cannot enable both 'parallel' and 'single_threaded' features. Choose one or the other.");

	/// Returns the current value of the global epoch counter.
	pub fn get_global_epochs(&self) -> u64 {
		self.global_epoch_counter.load(AtomicOrdering::Relaxed)
	}

	/// Returns the current value of the total iterations counter for this trainer instance.
	pub fn get_total_iterations(&self) -> u64 {
		self.total_iterations_counter.load(AtomicOrdering::Relaxed)
	}
	
	/// Get the shared InfoStatesMap
	pub fn infosets_map(&self) -> &Arc<InfoStatesMap> {
		&self.infosets
	}
	
	/// Returns the current position mapping
	pub fn get_current_position_mapping(&self) -> PositionMapping {
		self.rotation_schedule.get_mapping()
	}
	
	/// Advances the rotation schedule
	pub fn advance_rotation(&mut self) {
		self.rotation_schedule.advance();
	}

}

// --- Trainer Trait Implementations (Conditional) ---

#[cfg(feature = "parallel")]
impl<G, F> Trainer<G> for BaseTrainer<G, F>
where
	G: Game + Send + Sync + 'static,
	G::State: engine::state::State<Game = G> + 'static,
	F: Fn(
			Arc<G>,
			Arc<InfoStatesMap>,
			&CfrRngPool,
			SolverConfig,
		) -> Box<dyn PlayerAwareSolver<G> + Send + 'static>
		+ Send
		+ Sync
		+ 'static,
{
	fn run(&mut self, duration: std::time::Duration) -> GameResult<()> {
		debug!("[BaseTrainer] 'parallel' feature enabled, using multi-threaded run.");
		self._multi_threaded_run(duration)
	}

	fn average_policy(&self) -> Arc<TabularPolicy<G>> {
		let policy = regretmap::policy_helper::infosets_to_policy(
			&self.infosets,
			self.abstraction.clone(),
			true, // average policy
		);
		Arc::new(policy)
	}

	fn current_policy(&self) -> Arc<TabularPolicy<G>> {
		let policy = regretmap::policy_helper::infosets_to_policy(
			&self.infosets,
			self.abstraction.clone(),
			false, // current policy
		);
		Arc::new(policy)
	}
	fn iterations(&self) -> usize {
		self.iterations as usize
	}
	fn trainer_type_name(&self) -> &'static str {
		"BaseTrainer (Parallel Active)"
	}
	fn as_any(&self) -> &dyn Any {
		self
	}
	fn as_any_mut(&mut self) -> &mut dyn Any {
		self
	}
}

#[cfg(all(feature = "single_threaded", not(feature = "parallel")))]
impl<G, F> Trainer<G> for BaseTrainer<G, F>
where
	G: Game + Send + Sync + 'static,
	G::State: engine::state::State<Game = G> + 'static,
	F: Fn(
			Arc<G>,
			Arc<InfoStatesMap>,
			&CfrRngPool,
			SolverConfig,
		) -> Box<dyn PlayerAwareSolver<G> + Send + 'static>
		+ Send
		+ Sync
		+ 'static,
{
	fn run(&mut self, duration: std::time::Duration) -> GameResult<()> {
		self._single_threaded_run(duration)
	}

	fn average_policy(&self) -> Arc<TabularPolicy<G>> {
		Arc::new(regretmap::policy_helper::infosets_to_policy(
			&self.infosets,
			self.abstraction.clone(),
			true,
		))
	}
	fn current_policy(&self) -> Arc<TabularPolicy<G>> {
		Arc::new(regretmap::policy_helper::infosets_to_policy(
			&self.infosets,
			self.abstraction.clone(),
			false,
		))
	}
	fn iterations(&self) -> usize {
		self.iterations as usize
	}
	fn trainer_type_name(&self) -> &'static str {
		"BaseTrainer (SingleThreaded Only)"
	}
	fn as_any(&self) -> &dyn Any {
		self
	}
	fn as_any_mut(&mut self) -> &mut dyn Any {
		self
	}
}

// Implementation block for the private methods, not tied to the trait
// This block needs the same trait bounds as the public impl blocks.
impl<G, F> BaseTrainer<G, F>
where
	G: Game + Send + Sync + 'static,
	G::State: engine::state::State<Game = G> + 'static,
	F: Fn(
			Arc<G>,
			Arc<InfoStatesMap>,
			&CfrRngPool,
			SolverConfig,
		) -> Box<dyn PlayerAwareSolver<G> + Send + 'static>
		+ Send
		+ Sync
		+ 'static,
{
	#[cfg(feature = "parallel")]
	fn _multi_threaded_run(&mut self, duration: std::time::Duration) -> GameResult<()> {
		use std::sync::atomic::AtomicUsize;
		use std::thread;
		use std::time::Instant;

		let run_start_time = Instant::now(); // CAPTURE run start time
		let initial_epochs = self.get_global_epochs(); // CAPTURE initial epochs

		let ready_counter = Arc::new(AtomicUsize::new(0));
		let mut handles = Vec::with_capacity(self.num_threads);
		let deadline = Instant::now() + duration;

		// Clone Arcs and copy necessary data before the loop
		let game_clone = self.game.clone();
		let infosets_clone = self.infosets.clone();
		let factory_clone = self.solver_factory.clone();
		let rng_pool_clone = self.rng_pool.clone();
		let solver_config_copy = self.solver_config;
		let total_iterations_counter_clone = self.total_iterations_counter.clone();
		let global_epoch_counter_clone_outer = self.global_epoch_counter.clone(); // Renamed to avoid conflict
		let num_threads = self.num_threads;

		for thread_idx in 0..num_threads {
			// Move cloned Arcs and derive a per-thread RNG pool for deterministic streams
			let game = game_clone.clone();
			let num_players = game.num_players();
			let infosets = infosets_clone.clone();
			let factory = factory_clone.clone();
			let thread_seed = rng_pool_clone.base_seed().wrapping_add(thread_idx as u64);
			let rng_pool = CfrRngPool::from_seed(thread_seed);
			let solver_config = solver_config_copy;
			let total_iterations_counter = total_iterations_counter_clone.clone();
			let global_epoch_counter_clone = global_epoch_counter_clone_outer.clone();
			let ready = ready_counter.clone();
			let deadline_clone = deadline.clone();

			let handle = thread::spawn(move || -> u64 {
				ready.fetch_add(1, std::sync::atomic::Ordering::Release);

				// Create thread-local rotation schedule and set initial position context
				let mut local_rotation = RotationSchedule::new(num_players);
				let initial_mapping = local_rotation.get_mapping();
				set_position_context(Some(initial_mapping));

				let mut solver = (factory)(
					game.clone(),     // game is an Arc, clone it for the factory
					infosets.clone(), // infosets is an Arc, clone it for the factory
					&rng_pool,
					solver_config,
				);

				let mut local_sched = RoundRobin::new(num_players);
				let mut local_iters: u64 = 0;
				let mut num_local_cycles: usize = 0;
				let mut solver_warmed_up_for_this_thread = false;

				loop {
					let mut should_break = false;
					for _ in 0..solver_config.batch_size {
						let p = local_sched.next_player();
						solver.run_iteration_for_player(Some(p), &rng_pool);

						let num_cycles = local_sched.num_cycles();

						if num_cycles != num_local_cycles {
							num_local_cycles = num_cycles;

							let iter =
								total_iterations_counter.fetch_add(1, AtomicOrdering::Relaxed) + 1;
							solver.mark_iteration(iter);
							infosets.discount_decay().next_iter(iter); // Advance DiscountDecay
							infosets.increment_iterations(1); // Increment InfoStatesMap counter
							local_iters += 1;
							
							// TEMPORARILY DISABLED: Advance rotation and set position context
							// local_rotation.advance();
							let mapping = local_rotation.get_mapping();
							set_position_context(Some(mapping));

							match solver_config.epoch_method {
								EpochMethod::EveryIteration => {
									// bump every outer iteration
									global_epoch_counter_clone
										.fetch_add(1, AtomicOrdering::Relaxed);
								}
								EpochMethod::FixedEpoch => {
									// bump every K = solver_config.fixed_epoch_len iterations
									if iter % solver_config.fixed_epoch_len == 0 {
										global_epoch_counter_clone
											.fetch_add(1, AtomicOrdering::Relaxed);
									}
								}
							}

							if !solver_warmed_up_for_this_thread
								&& solver_config.warmup_iterations > 0
								&& local_iters >= solver_config.warmup_iterations as u64
							{
								solver.set_warmed_up();
								solver_warmed_up_for_this_thread = true;
							}
							
							// Check deadline every iteration to ensure responsive checkpoint timing
							if Instant::now() >= deadline_clone {
								should_break = true;
								break;
							}
						}
					}

					// If deadline was hit during the inner loop, break out of outer loop immediately
					if should_break {
						break;
					}

					if Instant::now() >= deadline_clone {
						// Use cloned deadline
						break;
					}
				}

				drop(solver);

				local_iters // RETURN only iterations
			});
			handles.push(handle);
		}

		debug!("[main] workers spawned");

		while ready_counter.load(std::sync::atomic::Ordering::Acquire) < num_threads {
			thread::sleep(Duration::from_millis(1));
		}

		let start = Instant::now();

		while start.elapsed() < duration {
			thread::sleep(Duration::from_millis(250));
		}

		debug!("[main] progress loop done, joining workers");

		let mut run_iterations = 0u64;
		for h in handles {
			if let Ok(n) = h.join() {
				run_iterations += n;
			}
		}

		debug!("[main] all joins finished");

		let _elapsed = start.elapsed(); // This `start` is for the progress loop, not the whole run.
								  // We use `run_start_time.elapsed()` for total wall clock.
		let wall_clock_this_run = run_start_time.elapsed();
		let _epochs_this_run = self.get_global_epochs() - initial_epochs;

		// Thread-local buffering is always active – nothing to toggle.

		// `elapsed` here refers to the time spent *after* workers were ready and spinning.
		// For overall rate, `wall_clock_this_run` is more appropriate.
		let rate = run_iterations as f64 / wall_clock_this_run.as_secs_f64().max(1e-9);

		debug!(
			"DONE {} iterations in {:.1?} ({:.1} it/s) – final infosets: {}",
			run_iterations,
			wall_clock_this_run, // USE wall_clock_this_run
			rate,
			0 // TODO: Add len() to ShardedTable
		);

		info!(
            "[BaseTrainer] Parallel run finished in {:.2?}. Iterations: {}. Rate: {:.1}/s. Final infosets: {}",
            wall_clock_this_run, // USE wall_clock_this_run
            run_iterations, rate, 0 // TODO: Add len() to ShardedTable
        );

		self.iterations += run_iterations; // This is iterations for the current run call.
									 // self.trainer_metrics.total_iterations_trainer accumulates across calls.
		
		// // Final publish to ensure all writes are visible
		// self.infosets.publish();
		
		Ok(())
	}

	#[cfg(any(
		feature = "single_threaded",
		not(any(feature = "parallel", feature = "single_threaded"))
	))]
	fn _single_threaded_run(&mut self, duration: std::time::Duration) -> GameResult<()> {
		use engine::scheduler::RoundRobin;
		use std::time::Instant;

		let run_start_time = Instant::now(); // CAPTURE run start time
		let initial_epochs = self.get_global_epochs(); // CAPTURE initial epochs

		let start = Instant::now(); // This `start` is for the loop timing, not total wall clock.
		let deadline = start + duration;
		let mut run_iterations: u64 = 0;

		// Set initial position context before creating solver
		let mapping = self.get_current_position_mapping();
		set_position_context(Some(mapping));

		let mut solver = (self.solver_factory.as_ref())(
			self.game.clone(),
			self.infosets.clone(),
			&self.rng_pool,
			self.solver_config,
		);

		let mut local_sched = RoundRobin::new(self.game.num_players());

		let mut last_num_cycles = 0;
		let mut solver_warmed_up = false;

		while Instant::now() < deadline {
			let p = local_sched.next_player();
			solver.run_iteration_for_player(Some(p), &self.rng_pool);

			let num_cycles = local_sched.num_cycles();
			if num_cycles != last_num_cycles {
				last_num_cycles = num_cycles;

				let iter = self
					.total_iterations_counter
					.fetch_add(1, AtomicOrdering::Relaxed)
					+ 1;
				solver.mark_iteration(iter);
				self.infosets.discount_decay().next_iter(iter); // Advance DiscountDecay
				self.infosets.increment_iterations(1); // Increment InfoStatesMap counter
				run_iterations += 1;
				
			// TEMPORARILY DISABLED: Advance rotation schedule and set position context
			// self.advance_rotation();
			
			// Set position context for solvers to use
			let mapping = self.get_current_position_mapping();
			set_position_context(Some(mapping));
				
				// DEBUG: Log position rotation
				if iter % 1000 == 0 {
					let mapping = self.get_current_position_mapping();
					eprintln!("DEBUG: Iteration {} - dealer position: {}", iter, mapping.dealer_button());
					
					// Publish periodically to make writes visible
					self.infosets.publish();
				}

				match self.solver_config.epoch_method {
					EpochMethod::EveryIteration => {
						// bump every outer iteration
						self.global_epoch_counter
							.fetch_add(1, AtomicOrdering::Relaxed);
					}
					EpochMethod::FixedEpoch => {
						// bump every K = self.solver_config.fixed_epoch_len iterations
						if iter % self.solver_config.fixed_epoch_len == 0 {
							self.global_epoch_counter
								.fetch_add(1, AtomicOrdering::Relaxed);
						}
					}
				}

				if !solver_warmed_up
					&& self.solver_config.warmup_iterations > 0
					&& iter >= self.solver_config.warmup_iterations as u64
				{
					solver.set_warmed_up();
					solver_warmed_up = true;
				}
			}

			if Instant::now() >= deadline {
				break;
			}
		}

		drop(solver);

		self.iterations += run_iterations; // Iterations for this specific run call

		let wall_clock_this_run = run_start_time.elapsed();
		let _epochs_this_run = self.get_global_epochs() - initial_epochs;

		let rate = run_iterations as f64 / wall_clock_this_run.as_secs_f64().max(1e-9);
		info!(
            "[BaseTrainer ST] Training completed in {:.2?}. Iterations: {}. Rate: {:.1}/s. Final infosets: {}",
            wall_clock_this_run, run_iterations, rate, 0 // TODO: Add len() to ShardedTable
        );

		// Final publish to ensure all writes are visible
		self.infosets.publish();

		Ok(())
	}
}

```

crates/poker-abs/src/leduc_rank_only.rs:
```
#![forbid(unsafe_code)]

//! Information abstraction for Leduc poker that ignores suits (rank only).
//!
//! This abstraction treats cards of the same rank as equivalent, regardless of
//! their suit. It hashes the player's hole card rank, the community card rank
//! (if revealed), and the betting history to generate the information state key.

use engine::{
    abstraction::InformationAbstraction,
    types::{CHANCE_PLAYER_ID, InfosetHashKey, PlayerId},
    position::{SeatNumber, ButtonSeat},
};
use games::leduc::{LeducGame, LeducState, constants::NUM_PLAYERS};
use rustc_hash::FxHasher;
use std::hash::{Hash, Hasher};

/// Zero-sized marker struct for the Leduc Rank-Only abstraction.
#[derive(Debug, Default, Clone, Copy)]
pub struct LeducRankOnlyAbs;

impl InformationAbstraction<LeducGame> for LeducRankOnlyAbs {
    fn key(&self, state: &LeducState, player: PlayerId) -> InfosetHashKey {
        if player >= NUM_PLAYERS {
            return InfosetHashKey(u64::MAX);
        }
        
        let mut hasher = FxHasher::default();
        
        // Hash the player's hole card rank only (no suit)
        if let Some(card) = state.hole_cards[player] {
            card.rank_index().hash(&mut hasher);
        } else {
            // No hole card dealt yet
            return InfosetHashKey(u64::MAX);
        }
        
        // Hash the community card rank only (no suit) if available
        if let Some(card) = state.community_card {
            card.rank_index().hash(&mut hasher);
        }
        
        
        for &(player_id, action) in &state.action_history {
            // Only hash betting actions, not chance actions
            if player_id != CHANCE_PLAYER_ID {
                let player_seat = SeatNumber::from(player_id);

                // let relative_pos = RelativePosition::from_seat_and_button(player_seat, button, NUM_PLAYERS);
                // relative_pos.as_u8().hash(&mut hasher);

                player_seat.hash(&mut hasher);
                action.0.hash(&mut hasher);
            }
        }
        
        // Hash the round number to distinguish pre/post community card states
        state.round.hash(&mut hasher);
        
        // // Hash the current player's relative position
        // let seat = SeatNumber::from(player);
        // let position = RelativePosition::from_seat_and_button(seat, button, NUM_PLAYERS);
        // (position.as_u8() as u64).hash(&mut hasher);
        
        InfosetHashKey(hasher.finish())
    }

    #[inline]
    fn id(&self) -> &'static str {
        "leduc_rank_only"
    }
}
```





Here's a regret update which shows  a nut hand with a better regret for check than bet:
```
    ╔══════════════════════════════════════════════════════════════════════╗
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ REGRET UPDATE - Infoset: 132695026057810103 Player: P0
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ GAME STATE:
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║   P0 hole: KS | P1 hole: QH | Community: KH
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║   Round: 1 | Pot: 6 | Stakes: 0
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║   History: Deal Deal P0:C P1:R P0:C Deal
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Action: 0 (Check) | ConcreteAction(1)
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Strategy: 0.6560 | Iteration: 6730
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Action Utility: 11.000000 | Node Value: 9.623885
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Immediate Regret: 1.376115 (action_util - node_value)
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Opponent CF Reach: 0.000026 | Player Reach: 0.021110
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Regret Delta: 0.000035 (opp_reach * immediate_regret)
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Regret Before: 0.001980
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Regret After:  0.002015
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ╚══════════════════════════════════════════════════════════════════════╝
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr]
    ╔══════════════════════════════════════════════════════════════════════╗
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ REGRET UPDATE - Infoset: 132695026057810103 Player: P0
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ GAME STATE:
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║   P0 hole: KS | P1 hole: QH | Community: KH
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║   Round: 1 | Pot: 6 | Stakes: 0
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║   History: Deal Deal P0:C P1:R P0:C Deal
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Action: 1 (Bet 4) | ConcreteAction(2)
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Strategy: 0.3440 | Iteration: 6730
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Action Utility: 7.000000 | Node Value: 9.623885
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Immediate Regret: -2.623885 (action_util - node_value)
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Opponent CF Reach: 0.000026 | Player Reach: 0.021110
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Regret Delta: -0.000067 (opp_reach * immediate_regret)
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Regret Before: 0.001039
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ║ Regret After:  0.000971
[2025-06-05T23:26:18Z DEBUG algorithms::external_sampling_cfr] ╚══════════════════════════════════════════════════════════════════════╝
```


```
    ╔══════════════════════════════════════════════════════════════════════╗
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ REGRET UPDATE - Infoset: 132695026057810103 Player: P0
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ GAME STATE:
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║   P0 hole: KS | P1 hole: QS | Community: KH
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║   Round: 1 | Pot: 6 | Stakes: 0
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║   History: Deal Deal P0:C P1:R P0:C Deal
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Action: 0 (Check) | ConcreteAction(1)
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Strategy: 0.8563 | Iteration: 23590
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Action Utility: 7.000000 | Node Value: 7.574959
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Immediate Regret: -0.574959 (action_util - node_value)
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Opponent CF Reach: 0.006350 | Player Reach: 0.196520
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Regret Delta: -0.003651 (opp_reach * immediate_regret)
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Regret Before: 0.471288
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Regret After:  0.467637
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ╚══════════════════════════════════════════════════════════════════════╝
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr]
    ╔══════════════════════════════════════════════════════════════════════╗
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ REGRET UPDATE - Infoset: 132695026057810103 Player: P0
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ GAME STATE:
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║   P0 hole: KS | P1 hole: QS | Community: KH
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║   Round: 1 | Pot: 6 | Stakes: 0
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║   History: Deal Deal P0:C P1:R P0:C Deal
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Action: 1 (Bet 4) | ConcreteAction(2)
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Strategy: 0.1437 | Iteration: 23590
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Action Utility: 11.000000 | Node Value: 7.574959
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Immediate Regret: 3.425041 (action_util - node_value)
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Opponent CF Reach: 0.006350 | Player Reach: 0.196520
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Regret Delta: 0.021749 (opp_reach * immediate_regret)
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ╠══════════════════════════════════════════════════════════════════════╣
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Regret Before: 0.079115
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ║ Regret After:  0.100864
[2025-06-06T00:01:06Z DEBUG algorithms::external_sampling_cfr] ╚══════════════════════════════════════════════════════════════════════╝
```


That is this scenario:
```
Key                | Player | Hole | Comm | Round | Action History (P0:C=Check/Call, P0:R=Raise, P0:F=Fold, D:Ks=Deal community)     | Policy [Fold, Call, Raise]
================================================================================================================================================================
132695026057810103 | P0     | Ks   | Kh   | R1    | P0:C    P1:R    P0:C    D:Kh                                                     | F:----       C:0.8192     R:0.1808
```

Running with RBP off, DCFR off, vector cards off, single threaded.

Vanillla and chance sampling both converge to 0.005 exploitability in 30s.


We have assertions that check for infosets with different legal actions.

It doesn't matter how long I let it run for.



Review the code, give me your best thoughts rooted in the code prioritzied as to what could be causing the issue.

If you give me an answer it has to compellingly explain without any magic:
1. Why it doesn't work with or without seat rotation (you like to assume my commented out testing code is the issue)
2. Why it doesn't work with or without fixed action order (first to act/second to act)
3. Why it doesn't work with infoset keys using fixed positions or relative positions
4. Why the same solver converges kuhn, and we have converged HULH & NLHE with it
5. WHy NO AMOUNT OF TIME changes the convergence properties
6. Why it doesn't matter if using identity abstraction or rank only abstraction
7. Why vanilla & CS CFR converge leduc just fine 
8. Adding in exploration rates don't change anything, still doesn't converge.
9. Switching to fixed betting actions where Fold is always in position (0) doesn't do anything (and hulh doesn't do this). I HAVE TRIED THIS BOTH WITH THE OPEN FOLD AND IWHTOUT AND YOU HAVE TOLD ME IT IS BOTH THIS AND NOT THIS MULTIPLE TIMES.
10. Asserts that infostates aren't changing legal actions don't go off
11. Why ES-CFR converges Kuhn poker which is *EVEN FUCKING SMALLER*
**DO NOT TELL ME IT IS THE OPEN FOLD WE HAVE GONE IN CIRCLES ON THIS**

