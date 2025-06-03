import { motion } from 'framer-motion';

interface ChatPillProps {
	onClick: () => void;
}

const ChatPill: React.FC<ChatPillProps> = ({ onClick }) => {
	return (
		<motion.div
			className="chat-pill fixed right-6 bottom-6 bg-cratejoy-teal text-white py-3 px-6 rounded-full shadow-lg z-30 flex items-center cursor-pointer hover:bg-cratejoy-dark transition duration-300"
			onClick={onClick}
			initial={{ y: 20, opacity: 0 }}
			animate={{ y: 0, opacity: 1 }}
			exit={{ y: 20, opacity: 0 }}
			whileHover={{ scale: 1.05 }}
			whileTap={{ scale: 0.95 }}
		>
			<svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
				<path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
			</svg>
			Chat with CJ Now
		</motion.div>
	);
};

export default ChatPill;
