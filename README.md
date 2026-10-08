# ArhInvest
ArhInvest Intelligent Assistant — A VK chat-bot developed to automate data collection, processing, and delivery regarding investment activities and municipal real estate objects.

This repository contains the source code for the VK bot backend, developed and successfully defended as a graduation thesis project.

## Usage

### Deployment & Configuration

Create a VK Community and enable bot features/tokens by following the [Official VK Bot API Guide](https://dev.vk.com/ru/api/bots/getting-started).

1. Clone the repository to your server/hosting environment and install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Сreate a `.env` file in the root directory and configure your VK API credentials:
   ```env
   VK_TOKEN=your_group_token_here
   ```
3. Launch the application to start the synchronous message polling loop:
   ```bash
   python main.py
   ```

### User Actions
Follow the following instructions

1. Trigger the «Торги» (Auctions) main section button.
2. Tap the next step navigational button marked with the «Вперед» (Forward) arrow emoji.
3. Select the «Комплексное развитие территорий» (Comprehensive Territory Development) subsection.
4. Click on «Итоги аукциона» (Auction Results) to open the target Document Card.
5. Follow the enclosed URL attachment in the description text to access the embedded document.
 
## Screenshots
### Menu «Sections»
<img width="455" height="676" alt="image" src="https://github.com/user-attachments/assets/a4476d76-3def-43d2-bc39-210bca034eab" />

### Menu «Subsections»
<img width="460" height="832" alt="image" src="https://github.com/user-attachments/assets/24e2f76d-e4ed-466b-aba9-5c8a9d11e958" />

## Contact
Email: [pavel.0x210@gmail.com](mailto:pavel.0x210@gmail.com)

